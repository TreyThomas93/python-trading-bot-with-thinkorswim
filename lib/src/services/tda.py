

from logging import Logger
from random import randint


class TDA:

    def __init__(self, accountId: int, accountInfo: dict, logger: Logger) -> None:
        self.accountId = accountId
        self.accountInfo = accountInfo
        self.logger = logger
        
    def connect(self) -> bool:
        return True

    def placeTDAOrder(self) -> dict:
        return {}

    def getQuote(self, symbol: str) -> dict:
        return {symbol: {"lastPrice": randint(1.00, 101.00)}}

    def getSpecificOrder(self, orderId: int) -> dict:
        return {
            'orderId': orderId,
            'status': 'FILLED',
            'price': randint(1.00, 101.00),
        }
