# SIM TRADER. BUYS/SELLS NO MATTER THE BUYING POWER

from pprint import pprint
from assets.current_datetime import getDatetime
import statistics
from datetime import datetime, timedelta
import pytz


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

            # print("SELL")
            # pprint(obj)

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

    def strategyResults(self):

        closed_positions = self.closed_positions.find({})

        strategy_results = {}

        for position in closed_positions:

            strategy = position["Strategy"]

            if strategy not in strategy_results:

                strategy_results[strategy] = {
                    "ROV": position["ROV"], "Wins": 0, "Loss": 0, "Flat": 0, "Avg": [], "Money_Gained": 0, "Money_Lost": 0}

            strategy_results[strategy]["ROV"] += position["ROV"]

            strategy_results[strategy]["Avg"].append(position["ROV"])

            if position["ROV"] >= 0.5:

                strategy_results[strategy]["Wins"] += 1

            elif position["ROV"] <= -0.5:

                strategy_results[strategy]["Loss"] += 1

            else:

                strategy_results[strategy]["Flat"] += 1

            profit_loss = position["Sell_Price"] - position["Buy_Price"]

            if profit_loss > 0:

                strategy_results[strategy]["Money_Gained"] += profit_loss

            else:

                strategy_results[strategy]["Money_Lost"] += profit_loss

        obj = {}

        for key, value in strategy_results.items():

            value["ROV"] = round(value["ROV"], 2)

            value["Avg"] = round(statistics.mean(value["Avg"]), 2)

            value["Money_Gained"] = round(value["Money_Gained"], 2)

            value["Money_Lost"] = round(value["Money_Lost"], 2)

            value["Profit_Loss"] = value["Money_Gained"] + value["Money_Lost"]

            obj[key] = value

        import pandas as pd
        from tabulate import tabulate

        df = pd.DataFrame(obj)

        print(tabulate(df, headers='keys', tablefmt='psql'))

    def topStrategy(self):
        """
        DETERMINE THE MOST PROFITABLE STRATEGY FOR EACH STOCK
        """

        closed_positions = self.closed_positions.find({})

        """
        SEPERATE STOCKS INTO DICT AS KEY AND HAVE ITS VALUE
        TO BE A LIST OF DICT WITH STRATEGY AS KEY AND VALUE AS ROV
        """

        stocks = {}

        for position in closed_positions:

            symbol = position["Symbol"]

            strategy = position["Strategy"]

            rov = position["ROV"]

            if symbol not in stocks:

                stocks[symbol] = {}

            if strategy not in stocks[symbol]:

                stocks[symbol][strategy] = []

            stocks[symbol][strategy].append(rov)

        """
        stocks = {
            "ABC" : {
                "LinRegEMA" : [],
                "IDK" : []
            }
        }
        """

        results = []

        for key, value in stocks.items():

            for k, v in value.items():

                stocks[key][k] = round(statistics.mean(v), 2)

        for key, value in stocks.items():

            strategy = max(value, key=value.get)

            avg = value[strategy]

            if avg >= 0 and strategy != "Sec_Agg_v2" and strategy != "Sec_Aggressive":

                results.append({
                    "Symbol": key,
                    "Avg_ROV": avg,
                    "Strategy": strategy
                })

        import pandas as pd
        from tabulate import tabulate

        df = pd.DataFrame(results)

        df = df.sort_values("Strategy", ignore_index=True)

        print(tabulate(df, headers='keys', tablefmt='psql'))

    def averageLength(self):

        # GET AVERAGE TRADE LENGTH FOR LINREGEMA_V2

        closed_positions = self.closed_positions.find(
            {"Strategy": "LinRegEMA_v2"})

        trade_diffs = []

        for position in closed_positions:

            delta = position["Sell_Date"] - position["Buy_Date"]

            trade_diffs.append(delta.days)

        avg = statistics.mean(trade_diffs)

        print(f"Average Trade Length: {round(avg, 2)} Days")

    def today(self):

        obj = {}

        closed_positions = self.closed_positions.find({})

        for i in range(20):

            dt = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

            obj[dt] = {"ROV": 0, "Positive": 0, "Negative": 0}

        for position in closed_positions:

            strategy = position["Strategy"]

            sell_date = position["Sell_Date"].strftime("%Y-%m-%d")

            rov = position["ROV"]

            if strategy == "LinRegEMA_v2":

                if sell_date in obj:

                    obj[sell_date]["ROV"] += rov

                    if rov > 0:

                        obj[sell_date]["Positive"] += 1

                    elif rov < 0:

                        obj[sell_date]["Negative"] += 1

        pprint(obj)

        # dt = datetime.now().strftime("%Y-%m-%d")

        # yd = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # for position in closed_positions:

        #     strategy = position["Strategy"]

        #     sell_date = position["Sell_Date"].strftime("%Y-%m-%d")

        #     rov = position["ROV"]

        #     if strategy == "LinRegEMA_v2":

        #         if sell_date == dt:

        #             todays_sells += 1

        #             if rov > 0:

        #                 pos += 1

        #             elif rov < 0:

        #                 neg += 1

        #         elif sell_date == yd:

        #             yesterdays_sells += 1

        # print(f"TODAYS SELLS: {todays_sells} - POSITIVE: {pos} - NEGATIVE: {neg}")

        # print(f"YESTERDAYS SELLS: {yesterdays_sells}")

        #     sell_date = position["Sell_Date"].strftime("%Y-%m-%d")

        #     strategy = position["Strategy"]

        #     symbol = position["Symbol"]

        #     if sell_date == dt and strategy == "LinRegEMA_v2":

        #         print(f"Symbol: {symbol} - Buy Price: {position['Buy_Price']} - Sell Price: {position['Sell_Price']} - ROV: {position['ROV']}")

        #         rov += position["ROV"]

        # print(rov)

    def sharpeRatio(self):

        from collections import OrderedDict

        strategy_results = {}

        closed_positions = self.closed_positions.find({})

        for position in closed_positions:

            # NEED PL FOR TRADE AND BUY PRICE
            buy_price = position["Buy_Price"]

            sell_price = position["Sell_Price"]

            profit_loss = sell_price - buy_price

            rov = profit_loss / buy_price

            strategy = position["Strategy"]

            if strategy not in strategy_results:

                strategy_results[strategy] = {
                    "Trade_Returns": [], "Wins": 0, "Loss": 0, "Drawdowns": []}

            strategy_results[strategy]["Trade_Returns"].append(rov)

            strategy_results[strategy]["Drawdowns"].append(profit_loss)
            # 5.041800000000002 -16.685000000000002
            # if strategy == "LinRegEMA_v2":

            #     if profit_loss == 12.79:
            #         print(f"Symbol: {position['Symbol']} - Buy Date: {position['Buy_Date']} - Sell Date: {position['Sell_Date']}, P/L: {profit_loss}")

            #     elif profit_loss == -9.96:
            #         print(f"Symbol: {position['Symbol']} - Buy Date: {position['Buy_Date']} - Sell Date: {position['Sell_Date']}, P/L: {profit_loss}")

            if profit_loss < 0:

                strategy_results[strategy]["Loss"] += 1

            elif profit_loss > 0:

                strategy_results[strategy]["Wins"] += 1

        for strategy, value in strategy_results.items():

            standard_dev = statistics.stdev(value["Trade_Returns"])

            avg_trade_returns = statistics.mean(value["Trade_Returns"])

            sharpe_ratio = avg_trade_returns / standard_dev
            #print(f"Strategy: {strategy} Returns: {round(avg_trade_returns, 4)} / STDev: {round(standard_dev, 4)} = SR: {round(sharpe_ratio, 4)} - RISK: {'LOW' if avg_trade_returns >= standard_dev else 'HIGH'}")
            # FIND MAX VALUE IN LIST
            max_value = max(value["Drawdowns"])

            # GET INDEX OF THAT VALUE
            max_index = value["Drawdowns"].index(max_value)

            # SEARCH FOR THE MIN FROM MAX INDEX TO THE END OF LIST
            min_value = min(value["Drawdowns"][max_index:])
            
            win_loss = ((value["Wins"] - value["Loss"]) /
                        value["Wins"]) * 100

            del strategy_results[strategy]["Trade_Returns"]

            del strategy_results[strategy]["Wins"]

            del strategy_results[strategy]["Loss"]

            del strategy_results[strategy]["Drawdowns"]

            strategy_results[strategy]["Sharpe_Ratio"] = round(sharpe_ratio, 2)

            # strategy_results[strategy]["Max_Drawdown"] = round(
            #     (min_value - max_value) / max_value, 2)

            strategy_results[strategy]["Max_Drawdown"] = round(
                max_value - min_value, 2)
            
            strategy_results[strategy]["W/L"] = round(win_loss, 2)

            # (AVG_ROV + W/L + SR) - MDD
            strategy_results[strategy]["Wow"] = ((avg_trade_returns / 100) + (win_loss / 100) + sharpe_ratio) - (max_value - min_value) / 100

        ordered = OrderedDict(sorted(strategy_results.items(
        ), key=lambda i: i[1]['Wow'], reverse=True))

        pprint(ordered)
