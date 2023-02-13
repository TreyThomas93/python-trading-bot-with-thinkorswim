
from datetime import datetime
from src.utils.helper import Helper
from src.models.enums import *


class Order:

    def __init__(self, symbol: str, side: Side, strategy: str, orderStatus: OrderStatus = OrderStatus.WORKING, orderId: int = None, quantity: int = 1, price: float = 0.0) -> None:
        self.symbol: str = symbol
        self.side: str = Helper.getSideEnum(side)
        self.strategy: str = strategy
        self.price: float = price
        self.quantity: int = quantity
        self.dt: datetime = datetime.now()
        self.orderId = orderId
        self.orderStatus = orderStatus

        self.orderType = None
        self.assetType = None
        self.session = None
        self.duration = None

    @classmethod
    def marketOrder(cls,  symbol: str, side: Side, strategy: str):
        instance = cls(symbol=symbol, side=side, strategy=strategy)
        instance.orderType: OrderType = OrderType.MARKET
        instance.assetType: str = AssetType.EQUITY
        instance.session: str = Session.NORMAL
        instance.duration: str = Duration.GOOD_TILL_CANCEL
        return instance

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

    @classmethod
    def fromJson(cls, order: dict):
        instance = cls(
            symbol=order["symbol"], side=order["side"], strategy=order["strategy"])
        instance.symbol = order["symbol"]
        instance.side = Helper.getSideEnum(order["side"])
        instance.strategy = order["strategy"]
        instance.price = order["price"]
        instance.quantity = order["quantity"]
        instance.dt = Helper.stringToDateTime(order["dt"])
        instance.orderId = order["orderId"]
        instance.orderStatus = Helper.getOrderStatusEnum(order["orderStatus"])
        instance.orderType = Helper.getOrderTypeEnum(order["orderType"])
        instance.assetType = Helper.getAssetTypeEnum(order["assetType"])
        instance.session = Helper.getSessionEnum(order["session"])
        instance.duration = Helper.getDurationEnum(order["duration"])
        return instance

    @property
    def marketOrderBracket(self) -> dict:
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
        return f"""Order(
            symbol: {self.symbol},
            side: {self.side},
            strategy: {self.strategy},
            price: {self.price},
            quantity: {self.quantity},
            dt: {self.dt},
            orderId: {self.orderId},
            orderStatus: {self.orderStatus}
        )"""
