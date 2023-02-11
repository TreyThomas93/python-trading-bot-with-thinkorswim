
from trader import Trader

extractedEmailData = ["Alert: New Symbol: ABC was added to REVA, SELL"]

if __name__ == "__main__":

    tradeDataObjects = []

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
                            tradeDataObjects.append({
                                "symbol": symbol.strip(),
                                "side": side.replace(".", " ").upper().strip(),
                                "strategy": strategy.replace(
                                    ".", " ").upper().strip(),
                            })

    Trader().trade(tradeDataObjects)
