# SIM TRADER. BUYS/SELLS NO MATTER THE BUYING POWER

from pprint import pprint
from assets.current_datetime import getDatetime
import statistics
from datetime import datetime, timedelta
import pytz
import requests


class SimTrader():

    def __init__(self, mongo):

        self.db = mongo.client["Sim_Trader"]

        self.open_positions = self.db["open_positions"]

        self.closed_positions = self.db["closed_positions"]

        self.eleven_check = False

    def buyOrder(self, symbol):

        try:

            aggregation = symbol["Aggregation"]

            strategy = symbol["Strategy"]

            symbol = symbol["Symbol"]

            resp = self.tdameritrade.getQuote(symbol)

            price = float(resp[symbol]["lastPrice"])

            shares = 1

            obj = {
                "Symbol": symbol,
                "Qty": shares,
                "Buy_Price": price,
                "Date": getDatetime(),
                "Strategy": strategy,
                "Aggregation": aggregation
            }

            # ADD TO OPEN POSITIONS
            self.open_positions.insert_one(obj)

            # print("BUY")
            # pprint(obj)

        except Exception as e:

            print("SIM TRADER - buyOrder", e)

    def sellOrder(self, symbol, position):

        try:

            aggregation = symbol["Aggregation"]

            strategy = symbol["Strategy"]

            symbol = symbol["Symbol"]

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
                "Aggregation": aggregation,
                "ROV": rov
            }

            # ADD TO CLOSED POSITIONS
            self.closed_positions.insert_one(obj)

            # REMOVE FROM OPEN POSITIONS
            self.open_positions.delete_one(
                {"Symbol": symbol, "Strategy": strategy})

            # SEND STRATEGY RESULT (IF YOU WANT TO)
            # email = "JohnDoe123@email.com"

            # self.sendStrategyResult(email, obj)

        except Exception as e:

            print("SIM TRADER - sellOrder", e)

    # SELL END OF DAY STOCK
    def sellOut(self, strategies):

        try:

            # GET ALL SECONDARY_AGG POSITIONS AND SELL THEM
            open_positions = self.open_positions.find({"$or": strategies})

            for position in open_positions:

                trade_data = {
                    "Symbol": position["Symbol"],
                    "Aggregation": position["Aggregation"],
                    "Strategy": position["Strategy"]
                }

                self.sellOrder(trade_data, position)

        except Exception as e:

            print("SIM TRADER - sellOut", e)

    def runTrader(self, symbols, tdameritrade):

        try:

            self.tdameritrade = tdameritrade

            for row in symbols["EQUITY"]:

                side = row["Side"]

                strategy = row["Strategy"]

                symbol = row["Symbol"]

                open_position = self.open_positions.find_one(
                    {"Symbol": symbol, "Strategy": strategy})

                forbidden_symbols = ["COTY", "MRO", "LGF/B", "PCG", "LGF/A"]

                if side == "BUY" and symbol not in forbidden_symbols:

                    if not open_position:

                        self.buyOrder(row)

                elif side == "SELL":

                    if open_position:

                        self.sellOrder(row, open_position)

        except Exception as e:

            print("SIM TRADER - runTrader", e)

        finally:

            dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

            dt_central = dt.astimezone(pytz.timezone('US/Central'))

            # SELL ALL Sec_Agg_Daytrade AT 14:30
            if dt_central.strftime("%H:%M") == "14:30":

                if not self.eleven_check:

                    self.sellOut([{"Strategy": "Sec_Aggressive"}])

                    self.eleven_check = True

            else:

                self.eleven_check = False

    def sendStrategyResult(self, email, obj):

        try:

            del obj["_id"]

            obj["Buy_Date"] = str(obj["Buy_Date"])

            obj["Sell_Date"] = str(obj["Sell_Date"])

            email = "TreyThomas93@gmail.com"

            resp = requests.post("https://treythomas673.pythonanywhere.com/api/send_strategy_result",
                                    json={"email": email, "trade_data": obj})

            print(resp.json(), resp.status_code)

        except Exception as e:

            print("POST REQUEST ERROR WHEN SENDING STRATEGY RESULT", e)