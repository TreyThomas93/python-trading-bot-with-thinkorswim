

from datetime import datetime
from logging import Logger
from random import randint
from src.models.user_model import User
from src.utils.helper import Helper
from src.models.enums import OrderStatus
from src.models.enums import Side, TradeType
from src.models.order_model import Order
from src.models.position_model import Position
from src.services.database import Database
from src.services.tda import TDA


class Trader(Database):

    def __init__(self, tda: TDA, user: User, logger: Logger) -> None:
        super().__init__()
        # set to [TradeType.LIVE] if you want to trade live
        self.tradeType: TradeType = TradeType.PAPER
        self.tda = tda
        self.user = user
        self.logger = logger

        self.logger.info(
            f"Trading session created for {Helper.modifiedAccountID(self.tda.accountId)} - User: {self.user.name}")

    def trade(self, orders: list) -> None:
        """starts the trading process.

        Args:
            orders (list): list of Order objects created from the emails.

        Returns:
            None
        """

        self.__checkOrderStatus()

        for order in orders:
            try:
                order: Order = Order.marketOrder(
                    accountId=self.tda.accountId, symbol=order['symbol'], side=order['side'], strategy=order['strategy'])
                openPosition = self.getOpenPosition(order)
                queued = self.checkIfInQueue(order)

                if queued:
                    continue

                # If no open position found and side is BUY, then create order
                if openPosition == None and order.side == Side.BUY:
                    self.logger.info(
                        f"Creating buy order for {order.symbol} - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                # If open position found and side is SELL, then create order
                elif openPosition != None and order.side == Side.SELL:
                    self.logger.info(
                        f"Creating sell order for {order.symbol} - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                else:
                    continue

                self.__sendOrder(order)
            except Exception as e:
                self.logger.error(
                    f"Error creating order for {order.symbol} - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}: {e}")

    def __sendOrder(self, order: Order) -> None:
        """Send order to TDAmeritrade if live, or to local database if paper.

        Args:
            order (Order): Order object to send to TDAmeritrade or local database.

        Returns:
            None
        """

        # can set quantity here based on anything. could query account balance and then divide by [lastPrice] of symbol to get quantity. defaults to 1.
        # order.quantity = 1

        orderId = None
        if self.tradeType == TradeType.LIVE:
            resp = self.tda.placeTDAOrder(order.marketOrderBracket)

            if resp.status_code not in [200, 201]:
                # TODO: Add to rejected orders database.
                self.logger.info(
                    f"Order {order.orderId} was rejected for {order.symbol} - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                return

            orderId = int(
                (resp.headers["Location"]).split("/")[-1].strip())

            self.logger.info(
                f"{order.side} order sent to TDA for {order.symbol} - User: {self.user.name} - OrderId: {orderId} - Quantity: {order.quantity} - Price: {order.price} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
        else:
            resp = self.tda.getQuote(order.symbol)

            order.price = float(resp[order.symbol]['lastPrice'])

            # generate random order id for paper trading.
            orderId = -1 * randint(100_000_000, 999_999_999)

        order.orderId = orderId

        self.queueOrder(order)

    def __checkOrderStatus(self) -> None:
        """Checks the status of all queued orders and handles according to new status fetched from TDA server.

        If paper trading, then just push order to local database.

        Returns:
            None
        """

        queued_orders = self.getQueuedOrders(accountId=self.tda.accountId)

        for order in queued_orders:

            try:

                order = Order.fromJson(order)

                orderId = order.orderId

                if self.tradeType == TradeType.PAPER:
                    self.__pushOrder(order, {
                        "price": order.price
                    })
                    continue

                specOrder = self.tda.getSpecificOrder(orderId)

                if "error" in specOrder:
                    self.logger.info(
                        f"An error occured while fetching order {orderId}. - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                    continue

                newStatus = Helper.getOrderStatusEnum(specOrder["status"])

                if orderId != specOrder["orderId"]:
                    # TODO: Add to rejected orders database.
                    self.logger.info(
                        f"Order {orderId} was not found. - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                    self.removeFromQueue(order)
                    continue

                # if status has not changed, then continue.
                if order.orderStatus == newStatus:
                    self.logger.info(
                        f'Order status has not changed. User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)} ')
                    continue

                match newStatus:
                    case OrderStatus.FILLED:
                        self.logger.info(
                            f"Pushing order {orderId} to local database - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                        self.__pushOrder(order, specOrder)
                    case OrderStatus.REJECTED | OrderStatus.CANCELED:
                        # TODO: Add to rejected orders database.
                        self.logger.info(
                            f"Order {orderId} was {newStatus}. - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                        self.removeFromQueue(order)
                    case _:
                        self.logger.info(
                            f"Order {orderId} is {newStatus}. - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
                        self.updateOrderStatus(order, newStatus)

            except Exception as e:
                self.logger.error(
                    f'Error checking order status - User: {self.user.name}: {e}')

    def __pushOrder(self, order: Order, specOrder: dict) -> None:
        """Pushes order to local database. If order is a buy order, then add to open positions database. If order is a sell order, then add to closed positions database.

        Args:
            order (Order): Order object to push to local database.
            specOrder (dict): Dictionary containing order details from TDA server.

        Returns:
            None
        """

        symbol = order.symbol
        price = float(specOrder["price"])
        price = round(price, 2) if price >= 1 else round(price, 4)
        order.price = price

        # If no open position found, then create new position and add to local database. [BUYING_POSITION]
        if order.side == Side.BUY:

            openPosition = Position(order)
            openPosition.tradeType = self.tradeType

            # Add position to local database
            self.addToOpenPositions(openPosition)

            self.logger.info(
                f"Added {symbol} to open positions - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")
        ############################################################
        # If open position found, then remove from open positions database and add to closed positions database. [SELLING_POSITION]
        elif order.side == Side.SELL:

            closedPosition = self.getOpenPosition(order)
            closedPosition.exitPrice = order.price
            closedPosition.exitDate = datetime.utcnow()
            closedPosition.orderId = order.orderId
            closedPosition.tradeType = self.tradeType

            # remove from open positions
            self.removeFromOpenPositions(order)

            # Update position to local database
            self.addToClosedPositions(closedPosition)

            self.logger.info(
                f"Added {symbol} to closed positions - User: {self.user.name} - Account ID: {Helper.modifiedAccountID(self.tda.accountId)}")

        # remove from queued orders
        self.removeFromQueue(order)
