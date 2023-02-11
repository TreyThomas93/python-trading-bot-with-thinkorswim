

from datetime import datetime
from models.enums import OrderStatus
from models.enums import Side, TradeType
from models.order_model import Order
from models.position_model import Position
from services.database import Database
from tda import TDA


class Trader(TDA, Database):

    def __init__(self) -> None:
        super().__init__()

        self.tradeType: TradeType = TradeType.PAPER

    def trade(self, tradeData: dict):
        for data in tradeData:
            openPosition = self.fetchPosition(data)
            queued = self.checkIfInQueue(data)

            if queued:
                continue

            order = None

            # If no open position found and side is BUY, then create order
            if openPosition == None and data["side"] == Side.BUY.value:
                print(f"Creating buy order")
                order = Order(data)
            # If open position found and side is SELL, then create order
            elif openPosition != None and data["side"] == Side.SELL.value:
                print(f"Creating sell order")
                order = Order(data)
            else:
                continue

            if order is not None:
                self.__sendOrder(order, openPosition)

    def __sendOrder(self, order: Order, openPosition: Position):

        if self.tradeType == TradeType.LIVE:
            pass
        else:
            # Fetch quote price from TDA and store in Position instance.
            pass

        print(f"{order.side} order sent to TDA - Trade Type: {self.tradeType.value}")

        # If no open position found, then create new position and add to local database. [BUYING_POSITION]
        if openPosition == None:

            # TODO: Only set [orderStatus] to FILLED if order is filled. Must check TDA to verify if filled.
            # position.orderStatus = OrderStatus.FILLED.value

            # Add position to local database
            self.addPosition(Position(order))
        ############################################################
        # If open position found, then update position and save to local database. [SELLING_POSITION]
        else:

            # TODO: Check TDA for last price.
            openPosition.exitPrice = 4.44
            openPosition.exitDate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # TODO: Only set [orderStatus] to FILLED if order is filled. Must check TDA to verify if filled.
            # openPosition.orderStatus = OrderStatus.FILLED.value
            # TODO: will be set to false once filled
            # openPosition.isOpen = False

            # Update position to local database
            self.updatePosition(openPosition)
