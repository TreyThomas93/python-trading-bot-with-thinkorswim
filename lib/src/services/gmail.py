

from src.models.order_model import Order
from src.trader import Trader


class Gmail:

    def __init__(self) -> None:
        pass

    def getEmails(self) -> list:
        extractedEmailData = ["Alert: New Symbol: ABC was added to REVA, SELL"]
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
