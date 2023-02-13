

from datetime import datetime
from random import randint
from src.models.enums import OrderStatus
from src.models.enums import Side, TradeType
from src.models.order_model import Order
from src.models.position_model import Position
from src.services.database import Database
from src.services.tda import TDA


class Trader(TDA, Database):

    def __init__(self) -> None:
        super().__init__()

        self.tradeType: TradeType = TradeType.PAPER

    def trade(self, orders: list):

        self.__checkOrderStatus()

        for order in orders:
            openPosition = self.getOpenPosition(order)
            queued = self.checkIfInQueue(order)

            if queued:
                continue

            # If no open position found and side is BUY, then create order
            if openPosition == None and order.side == Side.BUY:
                print(f"Creating buy order")
            # If open position found and side is SELL, then create order
            elif openPosition != None and order.side == Side.SELL:
                print(f"Creating sell order")
            else:
                continue

            self.__sendOrder(order)

    def __sendOrder(self, order: Order):

        order.quantity = 1

        orderId = None
        if self.tradeType == TradeType.LIVE:
            resp = self.placeTDAOrder(order)

            if resp.status_code not in [200, 201]:
                # TODO: Add to rejected orders database.
                return

            orderId = int(
                (resp.headers["Location"]).split("/")[-1].strip())

            print(
                f"{order.side} order sent to TDA")
        else:
            resp = self.getQuote(order.symbol)

            order.price = float(resp[order.symbol]['lastPrice'])

            # Fetch quote price from TDA and store in Position instance.
            orderId = -1*randint(100_000_000, 999_999_999)

        order.orderId = orderId

        self.queueOrder(order)

    def __checkOrderStatus(self):
        # TODO: Get all queued orders from local database.
        queued_orders = self.getQueuedOrders()

        # TODO: iterate over all queued orders and check TDA for order status.
        for order in queued_orders:

            orderId = order['orderId']

            order = Order(order)

            # if self.tradeType == TradeType.PAPER:
            #     self.__pushOrder(order, {
            #         "price": order.price
            #     })
            #     continue

            specOrder = self.getSpecificOrder(orderId)

            if "error" in specOrder:
                print(
                    f"An error occured while fetching order {orderId}.")
                continue

            newStatus = specOrder["status"]

            if orderId != specOrder["orderId"]:
                # TODO: Add to rejected orders database.
                print(f"Order {orderId} was not found.")
                self.removeFromQueue(order)
                continue
            
            # if status has not changed, then continue.
            if order.orderStatus == newStatus:
                print('Order status has not changed.')
                continue

            match newStatus:
                case "FILLED":
                    print(f"Pushing order {orderId} to local database.")
                    self.__pushOrder(order, specOrder)
                case "REJECTED" | "CANCELED":
                    # TODO: Add to rejected orders database.
                    print(f"Order {orderId} was {newStatus}.")
                    self.removeFromQueue(order)
                case _:
                    # TODO: Update order status in local database.
                    print(f"Order {orderId} is {newStatus}.")
                    self.updateOrderStatus(order, newStatus)

    def __pushOrder(self, order: Order, specOrder: dict):
        symbol = order.symbol
        price = float(specOrder["price"])
        price = round(price, 2) if price >= 1 else round(price, 4)
        order.price = price

        # If no open position found, then create new position and add to local database. [BUYING_POSITION]
        if order.side == Side.BUY:

            openPosition = Position(order)
            openPosition.tradeType = self.tradeType
            openPosition.orderStatus = OrderStatus.FILLED

            # Add position to local database
            self.addToOpenPositions(openPosition)

            print(f"Added {symbol} to open positions")
        ############################################################
        # If open position found, then update position and save to local database. [SELLING_POSITION]
        elif order.side == Side.SELL:

            closedPosition = self.getOpenPosition(order)
            closedPosition.exitPrice = order.price
            closedPosition.exitDate = datetime.now()
            closedPosition.orderId = order.orderId
            closedPosition.orderStatus = OrderStatus.FILLED
            closedPosition.tradeType = self.tradeType

            # remove from open positions
            self.removeFromOpenPositions(order)

            # Update position to local database
            self.addToClosedPositions(closedPosition)

            print(f"Added {symbol} to closed positions")

        # remove from queued orders
        self.removeFromQueue(order)
