

from random import randint


class TDA:

    def placeTDAOrder(self):
        pass

    def getQuote(self, symbol: str) -> dict:
        return {symbol: {"lastPrice": randint(1.00, 101.00)}}

    def getSpecificOrder(self, orderId: int) -> dict:
        return {
            'orderId': orderId,
            'status': 'WORKING',
            'price': 100.00,
        }
