from json_database import JsonStorage, JsonDatabase
from src.models.user_model import User
from src.models.order_model import Order
from src.models.enums import OrderStatus

from src.models.position_model import Position


class Database:

    def __init__(self) -> None:
        self.db = JsonStorage('db.conf')
        self.openPositionsDB = 'open_positions'
        self.closedPositionsDB = 'closed_positions'
        self.queuedOrdersDB = 'queued_orders'
        self.usersDB = 'users'
        self.path = 'lib/src/data'

    def getUsers(self) -> list:
        users = []
        with JsonDatabase(self.usersDB, f'{self.path}/{self.usersDB}.conf') as db:
            for user in db:
                users.append(User.fromJson(user))
        return users

    def addUser(self, user: User) -> None:
        with JsonDatabase(self.usersDB, f'{self.path}/{self.usersDB}.conf') as db:
            db.add_item(user.toJson())

    def queueOrder(self, order: Order):
        with JsonDatabase(self.queuedOrdersDB, f'{self.path}/{self.queuedOrdersDB}.conf') as db:
            db.add_item(order.toJson())

    def addToOpenPositions(self, position: Position) -> None:
        with JsonDatabase(self.openPositionsDB, f'{self.path}/{self.openPositionsDB}.conf') as db:
            db.add_item(position.toJson())

    def addToClosedPositions(self, position: Position) -> None:
        with JsonDatabase(self.closedPositionsDB, f'{self.path}/{self.closedPositionsDB}.conf') as db:
            db.add_item(position.toJson())

    def getOpenPosition(self, order: Order) -> Position:
        with JsonDatabase(self.openPositionsDB, f'{self.path}/{self.openPositionsDB}.conf') as db:
            for position in db:
                position: dict = position
                if position["symbol"] == order.symbol and position["strategy"] == order.strategy and position["accountId"] == order.accountId:
                    return Position.fromJson(position)
        return None

    def getQueuedOrders(self, accountId: int) -> list:
        queuedOrders = []
        with JsonDatabase(self.queuedOrdersDB, f'{self.path}/{self.queuedOrdersDB}.conf') as db:
            for position in db:
                if position["accountId"] == accountId:
                    queuedOrders.append(position)
        return queuedOrders

    def checkIfInQueue(self, order: Order) -> bool:
        with JsonDatabase(self.queuedOrdersDB, f'{self.path}/{self.queuedOrdersDB}.conf') as db:
            for queuedOrder in db:
                if queuedOrder["symbol"] == order.symbol and queuedOrder["strategy"] == order.strategy and queuedOrder["accountId"] == order.accountId:
                    return True
        return False

    def removeFromOpenPositions(self, order: Order) -> None:
        with JsonDatabase(self.openPositionsDB, f'{self.path}/{self.openPositionsDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy and pos["accountId"] == order.accountId:
                    db.remove_item(i)
                    break
                i += 1

    def removeFromQueue(self, order: Order) -> None:
        with JsonDatabase(self.queuedOrdersDB, f'{self.path}/{self.queuedOrdersDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy and pos["accountId"] == order.accountId:
                    db.remove_item(i)
                    break
                i += 1

    def updateOrderStatus(self, order: Order, status: OrderStatus) -> None:
        with JsonDatabase(self.queuedOrdersDB, f'{self.path}/{self.queuedOrdersDB}.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == order.symbol and pos["strategy"] == order.strategy and pos["accountId"] == order.accountId:
                    pos['orderStatus'] = status.value
                    db.update_item(i, pos)
                    break
                i += 1

    def updateUserAccountInfo(self, accountId: int, user: User) -> None:
        with JsonDatabase(self.usersDB, f'{self.path}/{self.usersDB}.conf') as db:
            i: int = 0
            for u in db:
                for id in u['accounts'].keys():
                    if int(id) == accountId:
                        db.update_item(i, user.toJson())
                        break
                i += 1
