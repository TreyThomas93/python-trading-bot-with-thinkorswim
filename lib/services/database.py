from json_database import JsonStorage, JsonDatabase
from models.order_model import Order
from models.enums import OrderStatus

from models.position_model import Position


class Database:

    def __init__(self) -> None:
        self.db = JsonStorage('db.conf')

    def addPosition(self, position: Position):
        with JsonDatabase("positions", 'positions.conf') as db:
            db.add_item(position)

    def updatePosition(self, position: Position):
        with JsonDatabase("positions", 'positions.conf') as db:
            i: int = 0
            for pos in db:
                if pos["symbol"] == position.symbol and pos["strategy"] == position.strategy and pos["isOpen"] == True:
                    db.update_item(i, position)
                    break
                i += 1

    def fetchPosition(self, tradeData: dict):
        with JsonDatabase("positions", 'positions.conf') as db:
            for position in db:
                position: dict = position
                if position["symbol"] == tradeData["symbol"] and position["strategy"] == tradeData["strategy"] and position["isOpen"] == True:
                    return Position(Order(position))
        return None

    def checkIfInQueue(self, tradeData: dict) -> bool:
        with JsonDatabase("positions", 'positions.conf') as db:
            for position in db:
                if position["symbol"] == tradeData["symbol"] and position["strategy"] == tradeData["strategy"] and position["orderStatus"] == OrderStatus.QUEUED.value:
                    return True
        return False
