# SIM TRADER. BUYS/SELLS NO MATTER THE BUYING POWER

from pprint import pprint
from assets.helper_functions import getDatetime
import statistics
from datetime import datetime, timedelta
import pytz
import requests


class PaperTrader():

    def __init__(self, mongo):

        self.db = mongo.client["Paper_Trader"]

        self.open_positions = self.db["open_positions"]

        self.closed_positions = self.db["closed_positions"]

    def openPosition(self, data):

        try:

            strategy = data["Strategy"]

            symbol = data["Symbol"]

            resp = self.tdameritrade.getQuote(symbol)

            price = float(resp[symbol]["lastPrice"])

            obj = {
                "Symbol": symbol,
                "Qty": 1,
                "Buy_Price": price,
                "Date": getDatetime(),
                "Strategy": strategy,
            }

            # ADD TO OPEN POSITIONS
            self.open_positions.insert_one(obj)

        except Exception as e:

            print("PAPER TRADER - openPosition", e)

    def closePosition(self, data, position):

        strategy = data["Strategy"]

        symbol = data["Symbol"]

        qty = position["Qty"]

        position_price = position["Buy_Price"]

        position_date = position["Date"]

        resp = self.tdameritrade.getQuote(symbol)

        price = float(resp[symbol]["lastPrice"])

        sell_price = round(price * qty, 2)

        buy_price = round(position_price * qty, 2)

        if buy_price != 0:

            rov = round(
                ((sell_price / buy_price) - 1) * 100, 2)

        else:

            rov = 0

        obj = {
            "Symbol": symbol,
            "Qty": qty,
            "Buy_Price": position_price,
            "Buy_Date": position_date,
            "Sell_Price": price,
            "Sell_Date": getDatetime(),
            "Strategy": strategy,
            "ROV": rov,
        }

        # ADD TO CLOSED POSITIONS
        self.closed_positions.insert_one(obj)

        # REMOVE FROM OPEN POSITIONS
        self.open_positions.delete_one(
            {"Symbol": symbol, "Strategy": strategy})

        # SEND STRATEGY RESULT (IF YOU WANT TO)
        # self.sendStrategyResult(obj)

    def runTrader(self, symbols, tdameritrade):

        try:

            self.tdameritrade = tdameritrade

            for row in symbols:

                side = row["Side"]

                strategy = row["Strategy"]

                symbol = row["Symbol"]

                open_position = self.open_positions.find_one(
                    {"Symbol": symbol, "Strategy": strategy})

                if side == "BUY":

                    # IF NO OPEN POSITION FOUND, BUY
                    if not open_position:

                        self.openPosition(row)

                elif side == "SELL":

                    # IF OPEN POSITION FOUND, SELL
                    if open_position:

                        self.closePosition(row, open_position)

        except Exception as e:

            print("PAPER TRADER - runTrader", e)

    def sendStrategyResult(self, obj):

        try:

            email = "JohnDoe123@email.com"

            del obj["_id"]

            obj["Buy_Date"] = str(obj["Buy_Date"])

            obj["Sell_Date"] = str(obj["Sell_Date"])

            email = "TreyThomas93@gmail.com"

            resp = requests.post("https://treythomas673.pythonanywhere.com/api/send_strategy_result",
                                 json={"email": email, "trade_data": obj})

            print(resp.json(), resp.status_code)

        except Exception as e:

            print("POST REQUEST ERROR WHEN SENDING STRATEGY RESULT", e)
