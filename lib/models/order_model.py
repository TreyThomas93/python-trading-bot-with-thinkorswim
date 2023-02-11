
from models.enums import *


class Order:

    def __init__(self, tradeData: dict):
        self.orderType: str = tradeData.get(
            "orderType", OrderType.MARKET.value)
        self.symbol: str = tradeData["symbol"]
        self.side: str = tradeData["side"]
        self.strategy: str = tradeData["strategy"]
        self.assetType: str = AssetType.EQUITY.value
        self.session: str = Session.NORMAL.value
        self.duration: str = Duration.GOOD_TILL_CANCEL.value
        self.price: float = 0.0
        self.quantity: int = 1

    @property
    def marketOrder(self) -> dict:
        return {
            "orderType": self.orderType,
            "session": self.session,
            "duration": self.duration,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": self.side,
                    "quantity": self.quantity,
                    "instrument": {
                        "symbol": self.symbol,
                        "assetType": self.assetType
                    }
                }
            ]
        }

    def __str__(self) -> str:
        return f"Order(Order Type: {self.orderType}, Symbol: {self.symbol}, Side: {self.side}, Strategy: {self.strategy}, Asset Type: {self.assetType}, Session: {self.session}, Duration: {self.duration}, Price: {self.price}, Quantity: {self.quantity})"
