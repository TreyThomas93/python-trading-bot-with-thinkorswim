

from datetime import datetime
from random import randint
from src.utils.helper import Helper
from src.models.enums import OrderStatus
from src.models.order_model import Order


class Position:

    def __init__(self, order: Order) -> None:
        self.orderId = order.orderId
        self.tradeType = None
        self.symbol = order.symbol
        self.side = order.side
        self.strategy = order.strategy
        self.assetType = order.assetType
        self.quantity = order.quantity

        # Entry
        self.entryPrice = order.price
        self.entryDate = datetime.now()

        # Exit
        self.exitDate = None
        self.exitPrice = None

    def toJson(self):
        return {
            "orderId": self.orderId,
            "tradeType": self.tradeType.value,
            "symbol": self.symbol,
            "side": self.side.value,
            "strategy": self.strategy,
            "assetType": self.assetType.value,
            "quantity": self.quantity,
            "orderStatus": self.orderStatus.value,
            "entryPrice": self.entryPrice,
            "entryDate": Helper.dateTimeToString(self.entryDate),
            "exitDate": Helper.dateTimeToString(self.exitDate),
            "exitPrice": self.exitPrice
        }

    def fromJson(self, json: dict):
        self.orderId = json["orderId"]
        self.tradeType = Helper.getTradeTypeEnum(json["tradeType"])
        self.symbol = json["symbol"]
        self.side = Helper.getSideEnum(json["side"])
        self.strategy = json["strategy"]
        self.assetType = Helper.getAssetTypeEnum(json["assetType"])
        self.quantity = json["quantity"]
        self.orderStatus = json["orderStatus"]
        self.entryPrice = json["entryPrice"]
        self.entryDate = Helper.stringToDateTime(json["entryDate"])
        self.exitDate = Helper.stringToDateTime(json["exitDate"])
        self.exitPrice = json["exitPrice"]
        return self

    def __str__(self) -> str:
        return f"""Position(
            orderId: {self.orderId},
            symbol: {self.symbol},
            side: {self.side},
            strategy: {self.strategy},
            assetType: {self.assetType},
            quantity: {self.quantity},
            orderStatus: {self.orderStatus},
            entryPrice: {self.entryPrice},
            entryDate: {self.entryDate},
            exitDate: {self.exitDate},
            exitPrice: {self.exitPrice}
        )"""
