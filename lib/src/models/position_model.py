

from datetime import datetime
from random import randint
from src.models.enums import AssetType, Side, TradeType
from src.utils.helper import Helper
from src.models.order_model import Order


class Position:

    def __init__(self, order: Order) -> None:
        self.orderId: int = order.orderId
        self.tradeType: TradeType = None
        self.symbol: str = order.symbol
        self.side: Side = order.side
        self.strategy: str = order.strategy
        self.assetType: AssetType = order.assetType
        self.quantity: int = order.quantity

        # Entry
        self.entryPrice: float = order.price
        self.entryDate: datetime = datetime.now()

        # Exit
        self.exitDate: float = None
        self.exitPrice: float = None

    def toJson(self):
        return {
            "orderId": self.orderId,
            "tradeType": self.tradeType.value,
            "symbol": self.symbol,
            "side": self.side.value,
            "strategy": self.strategy,
            "assetType": self.assetType.value,
            "quantity": self.quantity,
            "entryPrice": self.entryPrice,
            "entryDate": Helper.dateTimeToString(self.entryDate),
            "exitDate": Helper.dateTimeToString(self.exitDate),
            "exitPrice": self.exitPrice
        }

    @classmethod
    def fromJson(cls, json: dict):
        instance = cls(
            Order(symbol=json["symbol"], side=json["side"], strategy=json["strategy"]))
        instance.orderId = json["orderId"]
        instance.tradeType = Helper.getTradeTypeEnum(json["tradeType"])
        instance.symbol = json["symbol"]
        instance.side = Helper.getSideEnum(json["side"])
        instance.strategy = json["strategy"]
        instance.assetType = Helper.getAssetTypeEnum(json["assetType"])
        instance.quantity = json["quantity"]
        instance.entryPrice = json["entryPrice"]
        instance.entryDate = Helper.stringToDateTime(json["entryDate"])
        instance.exitDate = Helper.stringToDateTime(json["exitDate"])
        instance.exitPrice = json["exitPrice"]
        return instance

    def __str__(self) -> str:
        return f"""Position(
            orderId: {self.orderId},
            symbol: {self.symbol},
            side: {self.side},
            strategy: {self.strategy},
            assetType: {self.assetType},
            quantity: {self.quantity},
            entryPrice: {self.entryPrice},
            entryDate: {self.entryDate},
            exitDate: {self.exitDate},
            exitPrice: {self.exitPrice}
        )"""
