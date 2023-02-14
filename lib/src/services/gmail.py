

from random import randint
from src.models.order_model import Order
from src.trader import Trader

sides = ["BUY", "SELL"]

strategies = ['REVA', 'RSI_Swing', 'SMA_EMA']

_symbols = ['ABC', 'DEF', 'GHI']

class Gmail:

    def __init__(self) -> None:
        pass

    def getEmails(self) -> list:
        extractedEmailData = [
            f"Alert: New Symbol: {_symbols[randint(0, len(_symbols) - 1)]} was added to {strategies[randint(0, len(strategies) - 1)]}, {sides[randint(0, len(sides) - 1)]}"]
        tradeData: list = []

        for data in extractedEmailData:
            seperate = data.split(":")

            if len(seperate) > 1:

                contains = ["were added to", "was added to"]

                for i in contains:
                    if i in seperate[2]:
                        sep = seperate[2].split(i)
                        symbols = sep[0].strip().split(",")
                        strategy, side = sep[1].strip().split(",")

                        for symbol in symbols:
                            if strategy != "" and side != "":
                                tradeData.append({'symbol': symbol.strip(), 'side': side.replace(".", " ").upper().strip(), 'strategy': strategy.replace(
                                    ".", " ").upper().strip()
                                })

        return tradeData
