from json_database import JsonStorage, JsonDatabase
from src.models.order_model import Order
from src.models.enums import OrderStatus

from src.models.position_model import Position


class Database:

    def __init__(self) -> None:
        self.db = JsonStorage('db.conf')
        self.openPositionsDB = 'open_positions'
        self.closedPositionsDB = 'closed_positions'
        self.queuedOrdersDB = 'queued_orders'

    def queueOrder(self, order: Order):
        with JsonDatabase(self.queuedOrdersDB, f'{self.queuedOrdersDB}.conf') as db:
            db.add_item(order.toJson())

    def addToOpenPositions(self, position: Position) -> None:
        with JsonDatabase(self.openPositionsDB, f'{self.openPositionsDB}.conf') as db:
            db.add_item(position.toJson())

    def addToClosedPositions(self, position: Position) -> None:
        with JsonDatabase(self.closedPositionsDB, f'{self.closedPositionsDB}.conf') as db:
            db.add_item(position.toJson())

    def getOpenPosition(self, order: Order) -> Position:
        with JsonDatabase(self.openPositionsDB, f'{self.openPositionsDB}.conf') as db:
            for position in db:
                position: dict = position
                if position["symbol"] == order.symbol and position["strategy"] == order.strategy:
                    return Position(order).fromJson(position)
        return None

    def getQueuedOrders(self) -> list:
        queuedOrders = []
        with JsonDatabase(self.queuedOrdersDB, f'{self.queuedOrdersDB}.conf') as db:
            for position in db:
                queuedOrders.append(position)
        return queuedOrders

    def checkIfInQueue(self, order: Order) -> bool:
        with JsonDatabase(self.queuedOrdersDB, f'{self.queuedOrdersDB}.conf') as db:
            for queuedOrder in db:
                if queuedOrder["symbol"] == order.symbol and queuedOrder["strategy"] == order.strategy:
                    return True
        return False

    def removeFromOpenPositions(self, order: Order) -> None:
        with JsonDatabase(self.openPositionsDB, f'{self.openPositionsDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy:
                    db.remove_item(i)
                    print(f"Removed {order.symbol} from open positions")
                    break
                i += 1

    def removeFromQueue(self, order: Order) -> None:
        with JsonDatabase(self.queuedOrdersDB, f'{self.queuedOrdersDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy:
                    db.remove_item(i)
                    print(f"Removed {order.symbol} from queue")
                    break
                i += 1

    def updateOrderStatus(self, order: Order, status: str) -> None:
        with JsonDatabase(self.queuedOrdersDB, f'{self.queuedOrdersDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy:
                    pos['orderStatus'] = status
                    db.update_item(i, pos)
                    print(f"Updated {order.symbol} status to {status}")
                    break
                i += 1
