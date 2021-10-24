# imports
from assets.helper_functions import getDatetime


class OrderBuilder:

    def __init__(self):

        self.order = {
            "orderType": "LIMIT",
            "price": None,
            "session": None,
            "duration": None,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": None,
                    "quantity": None,
                    "instrument": {
                        "symbol": None,
                        "assetType": None,
                    }
                }
            ]
        }

        self.obj = {
            "Symbol": None,
            "Qty": None,
            "Position_Size": None,
            "Date": None,
            "Strategy": None,
            "Trader": self.user["Name"],
            "Order_ID": None,
            "Order_Status": None,
            "Side": None,
            "Asset_Type": None,
            "Account_ID": self.account_id,
            "Position_Type": None
        }

    def standardOrder(self, trade_data, strategy_object, OCOorder=False):

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        self.order["session"] = "SEAMLESS" if asset_type == "EQUITY" else "NORMAL"

        self.order["duration"] = "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY"

        self.order["orderLegCollection"][0]["instruction"] = side

        self.order["orderLegCollection"][0]["instrument"]["symbol"] = symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]

        self.order["orderLegCollection"][0]["instrument"]["assetType"] = asset_type

        self.obj["Symbol"] = symbol

        self.obj["Date"] = getDatetime()

        self.obj["Strategy"] = strategy

        self.obj["Side"] = side

        self.obj["Asset_Type"] = asset_type

        self.obj["Position_Type"] = strategy["Position_Type"]

        if asset_type == "OPTION":

            self.obj["Pre_Symbol"] = trade_data["Pre_Symbol"]

            self.obj["Exp_Date"] = trade_data["Exp_Date"]

            self.obj["Option_Type"] = trade_data["Option_Type"]

            self.order["orderLegCollection"][0]["instrument"]["putCall"] = trade_data["Option_Type"]

        # GET QUOTE FOR SYMBOL
        resp = self.tdameritrade.getQuote(
            symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

        price = float(resp[symbol]["bidPrice"]) if side in ["BUY", "BUY_TO_OPEN", "BUY_TO_CLOSE"] else float(
            resp[symbol]["askPrice"])

        # OCO ORDER NEEDS TO USE ASK PRICE FOR ISSUE WITH THE ORDER BEING TERMINATED UPON BEING PLACED
        if OCOorder:

            price = float(resp[symbol]["askPrice"])

        # WORK ON THIS!!!!!!!!!
        if side == "BUY" or side == "BUY_TO_OPEN":

            self.order["price"] = round(
                price, 2) if price >= 1 else round(price, 4)

            # GET SHARES FOR PARTICULAR STRATEGY
            strategy_object = self.strategies.find_one(
                {"Trader": self.user["Name"], "Strategy": strategy})

            if not strategy_object:

                self.addNewStrategy(strategy, asset_type)

                strategy_object = self.strategies.find_one(
                    {"Trader": self.user["Name"], "Strategy": strategy})

            active_strategy = strategy_object["Active"]

            position_size = int(strategy_object["Position_Size"])

            shares = int(
                position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

            if active_strategy and shares > 0:

                self.order["orderLegCollection"][0]["quantity"] = shares

                self.obj["Qty"] = shares

                self.obj["Position_Size"] = position_size

                self.obj["Buy_Price"] = price

            else:

                self.logger.WARNING(
                    __class__.__name__, f"{side} ORDER STOPPED: STRATEGY STATUS - {active_strategy} SHARES - {shares}")

                return None, None

        elif side == "SELL" or side == "SELL_TO_CLOSE":

            self.order["price"] = round(
                price, 2) if price >= 1 else round(price, 4)

            self.order["orderLegCollection"][0]["quantity"] = position_data["Qty"]

            self.obj["Buy_Price"] = position_data["Buy_Price"]

            self.obj["Buy_Date"] = position_data["Date"]

            self.obj["Qty"] = position_data["Qty"]

            self.obj["Position_Size"] = position_data["Position_Size"]
        ############################################################################
        
        return self.order, self.obj

    def OCOorder(self, trade_data, strategy_object):

        order, obj = self.standardOrder(trade_data, strategy_object, OCOorder=True)

        symbol = trade_data["Symbol"]

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        order["orderStrategyType"] = "TRIGGER"

        order["childOrderStrategies"] = [
            {
                "orderStrategyType": "OCO",
                "childOrderStrategies": [
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "LIMIT",
                        "price": None,
                        "orderLegCollection": [
                            {
                                "instruction": "SELL" if asset_type == "EQUITY" else "SELL_TO_CLOSE",
                                "quantity": None,
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    },
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "STOP",
                        "stopPrice": None,
                        "orderLegCollection": [
                            {
                                "instruction": "SELL" if asset_type == "EQUITY" else "SELL_TO_CLOSE",
                                "quantity": None,
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    }
                ]
            }
        ]

        return order, obj
