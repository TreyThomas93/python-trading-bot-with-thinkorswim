# imports
from assets.helper_functions import getDatetime


class PaperTrader():

    def __init__(self, mongo, logger):

        self.strategies = mongo.strategies

        self.db = mongo.client["Paper_Trader"]

        self.open_positions = self.db["open_positions"]

        self.closed_positions = self.db["closed_positions"]

        self.logger = logger

    def openPosition(self, data):

        try:

            strategy = data["Strategy"]

            symbol = data["Symbol"]

            position_type = data["Position_Type"]

            asset_type = data["Asset_Type"]

            resp = self.tdameritrade.getQuote(symbol)

            price = float(resp[symbol]["lastPrice"])

            obj = {
                "Symbol": symbol,
                "Qty": 1,
                "Buy_Price": price,
                "Date": getDatetime(),
                "Strategy": strategy,
                "Position_Type": position_type,
                "Asset_Type": asset_type
            }

            # ADD TO OPEN POSITIONS
            self.open_positions.insert_one(obj)

        except Exception as e:

            self.logger.ERROR(f"{__class__.__name__} - openPosition - {e}")

    def closePosition(self, data, position):

        try:

            strategy = data["Strategy"]

            symbol = data["Symbol"]

            qty = position["Qty"]

            position_price = position["Buy_Price"]

            position_date = position["Date"]

            position_type = position["Position_Type"]

            asset_type = position["Asset_Type"]

            resp = self.tdameritrade.getQuote(symbol)

            price = float(resp[symbol]["lastPrice"])

            sell_price = round(price * qty, 2)

            buy_price = round(position_price * qty, 2)

            if buy_price != 0:

                if position_type == "Long":

                    rov = round(
                        ((sell_price / buy_price) - 1) * 100, 2)

                elif position_type == "Short":

                    rov = round(
                        ((buy_price / sell_price) - 1) * 100, 2)

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
                "Position_Type": position_type,
                "Asset_Type": asset_type,
            }

            # ADD TO CLOSED POSITIONS
            self.closed_positions.insert_one(obj)

            # REMOVE FROM OPEN POSITIONS
            self.open_positions.delete_one(
                {"Symbol": symbol, "Strategy": strategy})

        except Exception as e:

            self.logger.ERROR(f"{__class__.__name__} - closePosition - {e}")

    def runTrader(self, symbols, tdameritrade):

        try:

            self.tdameritrade = tdameritrade

            for row in symbols:

                side = row["Side"]

                strategy = row["Strategy"]

                symbol = row["Symbol"]

                open_position = self.open_positions.find_one(
                    {"Symbol": symbol, "Strategy": strategy})

                strategy_position_type = self.strategies.find_one(
                    {"Strategy": strategy})["Position_Type"]

                row["Position_Type"] = strategy_position_type

                # USE STRATEGY_POSITION_TYPE TO DETERMINE IF ALERT NEEDS TO GO LONG OR SHORT
                # MyRSIStrategy, BUY, 123456789
                # MyRSIStrategy, SELL, 123456789
                # MyRSIStrategy - LONG
                # THEREFORE, IF A SELL ALERT AND STRATEGY IS LONG, THE BOT KNOWS TO SELL LONG, AND NOT GO SHORT
                # THEREFORE, IF A BUY ALERT AND STRATEGY IS SHORT, THE BOT KNOWS TO BUY SHORT, AND NOT GO LONG

                # EQUITY
                if side == "BUY":

                    # IF BUY ORDER FOR LONG POSITION
                    if strategy_position_type == "Long" and not open_position:

                        self.openPosition(row)

                    # IF BUY ORDER FOR SHORT POSITION
                    elif strategy_position_type == "Short" and open_position:

                        self.closePosition(row, open_position)

                # EQUITY
                elif side == "SELL":

                    # IF SELL ORDER FOR LONG POSITION
                    if strategy_position_type == "Long" and open_position:

                        self.closePosition(row, open_position)

                    # IF SELL ORDER FOR SHORT POSITION
                    elif strategy_position_type == "Short" and not open_position:

                        self.openPosition(row)

                # OPTION
                elif side in ["BUY_TO_OPEN", "SELL_TO_OPEN"]:

                    if not open_position:

                        # CHECKS TO MAKE SURE THE POSITION TYPES MATCH UP WITH THE STRATEGY POSITION TYPE
                        if (side == "BUY_TO_OPEN" and strategy_position_type == "Long") or (side == "SELL_TO_OPEN" and strategy_position_type == "Short"):

                            self.openPosition(row)

                # OPTION
                elif side in ["BUY_TO_CLOSE", "SELL_TO_CLOSE"]:

                    if open_position:

                        # CHECKS TO MAKE SURE THE POSITION TYPES MATCH UP WITH THE STRATEGY POSITION TYPE
                        if (side == "BUY_TO_CLOSE" and strategy_position_type == "Short") or (side == "SELL_TO_CLOSE" and strategy_position_type == "Long"):

                            self.closePosition(row, open_position)

        except Exception as e:

            self.logger.ERROR(f"{__class__.__name__} - runTrader - {e}")
