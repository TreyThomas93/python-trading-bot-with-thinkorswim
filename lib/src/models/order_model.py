
from datetime import datetime
from src.utils.helper import Helper
from src.models.enums import *


class Order:

    def __init__(self, tradeData: dict):
        self.orderType: str = tradeData.get(
            "orderType", OrderType.MARKET)
        self.symbol: str = tradeData["symbol"]
        self.side: str = Helper.getSideEnum(tradeData["side"])
        self.strategy: str = tradeData["strategy"]
        self.assetType: str = AssetType.EQUITY
        self.session: str = Session.NORMAL
        self.duration: str = Duration.GOOD_TILL_CANCEL
        self.price: float = tradeData.get('price') or 0.0
        self.quantity: int = tradeData.get('quantity') or 0
        self.dt: datetime = datetime.now()
        self.orderId = tradeData.get('orderId') or 0
        self.orderStatus = tradeData.get('orderStatus') or None

    def toJson(self) -> dict:
        return {
            "orderType": self.orderType.value,
            "symbol": self.symbol,
            "side": self.side.value,
            "strategy": self.strategy,
            "assetType": self.assetType.value,
            "session": self.session.value,
            "duration": self.duration.value,
            "price": self.price,
            "quantity": self.quantity,
            "dt": Helper.dateTimeToString(self.dt),
            "orderId": self.orderId,
            'orderStatus': self.orderStatus.value if self.orderStatus != None else None
        }

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
        return f"Order(Order Type: {self.orderType}, Symbol: {self.symbol}, Side: {self.side}, Strategy: {self.strategy}, Asset Type: {self.assetType}, Session: {self.session}, Duration: {self.duration}, Price: {self.price}, Quantity: {self.quantity}, Date Time: {self.dt}, Order ID: {self.orderId}, Order Status: {self.orderStatus})"
