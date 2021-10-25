# imports
from assets.helper_functions import getDatetime
from dotenv import load_dotenv
from pathlib import Path
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

BUY_PRICE = os.getenv('BUY_PRICE')
SELL_PRICE = os.getenv('SELL_PRICE')
TAKE_PROFIT_PERCENTAGE = float(os.getenv('TAKE_PROFIT_PERCENTAGE'))
STOP_LOSS_PERCENTAGE = float(os.getenv('STOP_LOSS_PERCENTAGE'))


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
            "Strategy": None,
            "Trader": self.user["Name"],
            "Order_ID": None,
            "Order_Status": None,
            "Side": None,
            "Asset_Type": None,
            "Account_ID": self.account_id,
            "Position_Type": None
        }

    def standardOrder(self, trade_data, strategy_object, direction, OCOorder=False):

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        # TDA ORDER OBJECT
        self.order["session"] = "SEAMLESS" if asset_type == "EQUITY" else "NORMAL"

        self.order["duration"] = "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY"

        self.order["orderLegCollection"][0]["instruction"] = side

        self.order["orderLegCollection"][0]["instrument"]["symbol"] = symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]

        self.order["orderLegCollection"][0]["instrument"]["assetType"] = asset_type
        ##############################################################

        # MONGO OBJECT
        self.obj["Symbol"] = symbol

        self.obj["Strategy"] = strategy

        self.obj["Side"] = side

        self.obj["Asset_Type"] = asset_type

        self.obj["Position_Type"] = strategy_object["Position_Type"]

        self.obj["Order_Type"] = strategy_object["Order_Type"]
        ##############################################################

        if asset_type == "OPTION":

            self.obj["Pre_Symbol"] = trade_data["Pre_Symbol"]

            self.obj["Exp_Date"] = trade_data["Exp_Date"]

            self.obj["Option_Type"] = trade_data["Option_Type"]

            self.order["orderLegCollection"][0]["instrument"]["putCall"] = trade_data["Option_Type"]

        # GET QUOTE FOR SYMBOL
        resp = self.tdameritrade.getQuote(
            symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

        price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]][BUY_PRICE]) if side in ["BUY", "BUY_TO_OPEN", "BUY_TO_CLOSE"] else float(
            resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]][SELL_PRICE])

        # OCO ORDER NEEDS TO USE ASK PRICE FOR ISSUE WITH THE ORDER BEING TERMINATED UPON BEING PLACED
        if OCOorder:

            price = float(resp[symbol][SELL_PRICE])

        self.order["price"] = round(
            price, 2) if price >= 1 else round(price, 4)

        # IF OPENING POSITION
        if direction == "OPEN POSITION":

            position_size = int(strategy_object["Position_Size"])

            shares = int(
                position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

            if strategy_object["Active"] and shares > 0:

                self.order["orderLegCollection"][0]["quantity"] = shares

                self.obj["Qty"] = shares

                self.obj["Position_Size"] = position_size

                self.obj["Entry_Price"] = price

                self.obj["Entry_Date"] = getDatetime()

            else:

                self.logger.WARNING(
                    __class__.__name__, f"{side} ORDER STOPPED: STRATEGY STATUS - {strategy_object['Active']} SHARES - {shares}")

                return None, None

        # IF CLOSING A POSITION
        elif direction == "CLOSE POSITION":

            self.order["orderLegCollection"][0]["quantity"] = trade_data["Qty"]

            self.obj["Entry_Price"] = trade_data["Entry_Price"]

            self.obj["Entry_Date"] = trade_data["Entry_Date"]

            self.obj["Exit_Price"] = trade_data["Exit_Price"]

            self.obj["Exit_Date"] = trade_data["Exit_Date"]

            self.obj["Qty"] = trade_data["Qty"]

            self.obj["Position_Size"] = trade_data["Position_Size"]
        ############################################################################

        return self.order, self.obj

    def OCOorder(self, trade_data, strategy_object, direction):

        order, obj = self.standardOrder(
            trade_data, strategy_object, direction, OCOorder=True)

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        side = trade_data["Side"]

        if side == "BUY_TO_OPEN":

            instruction = "SELL_TO_CLOSE"

        elif side == "BUY":

            instruction = "SELL"

        elif side == "SELL":

            instruction = "BUY"

        elif side == "SELL_TO_OPEN":

            instruction = "BUY_TO_CLOSE"

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
                        "price": round(
                            order["price"] * TAKE_PROFIT_PERCENTAGE, 2) if order["price"] * TAKE_PROFIT_PERCENTAGE >= 1 else round(order["price"] * TAKE_PROFIT_PERCENTAGE, 4),
                        "orderLegCollection": [
                            {
                                "instruction": instruction,
                                "quantity": obj["Qty"],
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": trade_data["Symbol"] if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    },
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "STOP",
                        "stopPrice": round(order["price"] * STOP_LOSS_PERCENTAGE, 2) if order["price"] * STOP_LOSS_PERCENTAGE >= 1 else round(order["price"] * STOP_LOSS_PERCENTAGE, 4),
                        "orderLegCollection": [
                            {
                                "instruction": instruction,
                                "quantity": obj["Qty"],
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": trade_data["Symbol"] if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    }
                ]
            }
        ]

        return order, obj
