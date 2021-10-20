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
        }

    def standardOrder(self, trade_data, position_data=None):

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

        if asset_type == "OPTION":

            self.obj["Pre_Symbol"] = trade_data["Pre_Symbol"]

            self.obj["Exp_Date"] = trade_data["Exp_Date"]

            self.obj["Option_Type"] = trade_data["Option_Type"]

            self.order["orderLegCollection"][0]["instrument"]["putCall"] = trade_data["Option_Type"]

        if side == "BUY" or side == "BUY_TO_OPEN":

            # GET QUOTE FOR SYMBOL
            resp = self.tdameritrade.getQuote(
                symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

            price = float(
                resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]]["bidPrice"])

            self.order["price"] = round(
                price, 2) if price >= 1 else round(price, 4)

            # GET SHARES FOR PARTICULAR STRATEGY
            strategies = self.user["Accounts"][str(
                self.account_id)]["Strategies"]

            if strategy not in strategies:

                self.updateStrategiesObject(strategy)

                strategies = self.mongo.users.find_one({"Name": self.user["Name"]})["Accounts"][str(
                    self.account_id)]["Strategies"]

            position_size = int(strategies[strategy]["Position_Size"])

            active_strategy = strategies[strategy]["Active"]

            shares = int(position_size/price)

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

            resp = self.tdameritrade.getQuote(
                symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

            price = float(resp[symbol]["askPrice"])

            self.order["price"] = round(
                price, 2) if price >= 1 else round(price, 4)

            self.order["orderLegCollection"][0]["quantity"] = position_data["Qty"]

            self.obj["Buy_Price"] = position_data["Buy_Price"]

            self.obj["Buy_Date"] = position_data["Date"]

            self.obj["Qty"] = position_data["Qty"]

            self.obj["Position_Size"] = position_data["Position_Size"]

        return self.order, self.obj

    def OCOorder(self, trade_data):

        order, obj = self.standardOrder(trade_data)

        symbol = trade_data["Symbol"]

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
                                "instruction": "SELL",
                                "quantity": None,
                                "instrument": {
                                    "assetType": "EQUITY",
                                    "symbol": symbol
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
                                "instruction": "SELL",
                                "quantity": None,
                                "instrument": {
                                    "assetType": "EQUITY",
                                    "symbol": "XYZ"
                                }
                            }
                        ]
                    }
                ]
            }
        ]

        return order, obj
