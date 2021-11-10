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

            price = float(resp[symbol][BUY_PRICE]) if position_type == "LONG" else float(
                resp[symbol][SELL_PRICE])

            obj = {
                "Symbol": symbol,
                "Qty": 1,
                "Entry_Price": price,
                "Entry_Date": getDatetime(),
                "Strategy": strategy,
                "Position_Type": position_type,
                "Asset_Type": asset_type
            }

            # ADD TO OPEN POSITIONS
            self.open_positions.insert_one(obj)

            msg = f"PAPER TRADER OPENED A POSITION - SYMBOL: {symbol} - STRATEGY: {strategy} - POSITION TYPE: {position_type} - ASSET TYPE: {asset_type}\n"

            self.logger.info(msg)

        except Exception as e:

            self.logger.error(f"{__class__.__name__} - openPosition - {e}")

    def closePosition(self, data, position):

        try:

            strategy = data["Strategy"]

            symbol = data["Symbol"]

            qty = position["Qty"]

            entry_price = position["Entry_Price"]

            entry_date = position["Entry_Date"]

            position_type = position["Position_Type"]

            asset_type = position["Asset_Type"]

            resp = self.tdameritrade.getQuote(symbol)

            if position_type == "LONG":

                price = float(resp[symbol][BUY_PRICE])

                exit_price = round(price * qty, 2)

                entry_price = round(entry_price * qty, 2)

                rov = round(
                    ((exit_price / entry_price) - 1) * 100, 2)

            elif position_type == "SHORT":

                price = float(resp[symbol][SELL_PRICE])

                exit_price = round(price * qty, 2)

                entry_price = round(entry_price * qty, 2)

                rov = round(
                    ((entry_price / exit_price) - 1) * 100, 2)

            else:

                rov = 0

            obj = {
                "Symbol": symbol,
                "Qty": qty,
                "Entry_Price": entry_price,
                "Entry_Date": entry_date,
                "Exit_Price": price,
                "Exit_Date": getDatetime(),
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

            msg = f"PAPER TRADER CLOSED A POSITION - SYMBOL: {symbol} - STRATEGY: {strategy} - POSITION TYPE: {position_type} - ASSET TYPE: {asset_type}\n"

            self.logger.info(msg)

        except Exception as e:

            self.logger.error(f"{__class__.__name__} - closePosition - {e}")

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

                # EQUITY
                if side == "BUY":

                    # IF BUY ORDER FOR LONG POSITION
                    if strategy_position_type == "LONG" and not open_position:

                        self.openPosition(row)

                    # IF BUY ORDER FOR SHORT POSITION
                    elif strategy_position_type == "SHORT" and open_position:

                        self.closePosition(row, open_position)

                # EQUITY
                elif side == "SELL":

                    # IF SELL ORDER FOR LONG POSITION
                    if strategy_position_type == "LONG" and open_position:

                        self.closePosition(row, open_position)

                    # IF SELL ORDER FOR SHORT POSITION
                    elif strategy_position_type == "SHORT" and not open_position:

                        self.openPosition(row)

                # OPTION
                elif side in ["BUY_TO_OPEN", "SELL_TO_OPEN"]:

                    if not open_position:

                        # CHECKS TO MAKE SURE THE POSITION TYPES MATCH UP WITH THE STRATEGY POSITION TYPE
                        if (side == "BUY_TO_OPEN" and strategy_position_type == "LONG") or (side == "SELL_TO_OPEN" and strategy_position_type == "SHORT"):

                            self.openPosition(row)

                # OPTION
                elif side in ["BUY_TO_CLOSE", "SELL_TO_CLOSE"]:

                    if open_position:

                        # CHECKS TO MAKE SURE THE POSITION TYPES MATCH UP WITH THE STRATEGY POSITION TYPE
                        if (side == "BUY_TO_CLOSE" and strategy_position_type == "SHORT") or (side == "SELL_TO_CLOSE" and strategy_position_type == "LONG"):

                            self.closePosition(row, open_position)

        except Exception as e:

            self.logger.error(f"{__class__.__name__} - runTrader - {e}")
