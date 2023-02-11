

from datetime import datetime
from random import randint
from models.enums import OrderStatus
from models.order_model import Order


class Position:

    def __init__(self, order: Order) -> None:
        self.orderId = -1*randint(100_000_000, 999_999_999)
        self.tradeType = None
        self.symbol = order.symbol
        self.side = order.side
        self.strategy = order.strategy
        self.assetType = order.assetType
        self.quantity = order.quantity
        self.orderStatus: OrderStatus = OrderStatus.QUEUED.value
        self.orderBracket: dict = None

        # Entry
        self.entryPrice = order.price
        self.entryDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.isOpen = True

        # Exit
        self.exitDate = None
        self.exitPrice = None

    def __str__(self) -> str:
        return f"Position(Order ID: {self.orderId}, Trade Type: {self.tradeType}, Symbol: {self.symbol}, Side: {self.side}, Strategy: {self.strategy}, Asset Type: {self.assetType}, Quantity: {self.quantity}, Entry Price: {self.entryPrice}, Entry Date: {self.entryDate}, Exit Price: {self.exitPrice}, Exit Date: {self.exitDate}, Is Open: {self.isOpen}, Order Status: {self.orderStatus})"
