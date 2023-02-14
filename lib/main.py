

from logging import Formatter
import logging
import os
import time
from src.utils.multifilehandler import MultiFileHandler
from src.services.tda import TDA
from src.models.user_model import User
from src.services.database import Database
from src.services.gmail import Gmail
from src.trader import Trader


class Main(Database):

    def __init__(self) -> None:
        super().__init__()

        file_handler = MultiFileHandler(
            filename=f'{os.path.abspath(os.path.dirname(__file__))}/src/utils/logs/info.log', mode='a')
        formatter = Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        ch = logging.StreamHandler()
        ch.setLevel(level="INFO")
        ch.setFormatter(formatter)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level="INFO")
        self.logger.addHandler(file_handler)
        self.logger.addHandler(ch)

        self.gmail = Gmail()
        self.usersToTrade = {}
        self.usersNotConnected = []

        self.logger.info(
            "Starting Trading Bot...")

        print("\n--------------------------------------------------\n")

    def setupUsers(self):

        users = self.getUsers()
        for user in users:
            user: User = user
            try:
                for accountId in user.accounts.keys():
                    if accountId not in self.usersToTrade and accountId not in self.usersNotConnected:
                        tda = TDA(int(accountId),
                                  user.accounts[accountId], self.logger)
                        connected = tda.connect()

                        if not connected:
                            self.usersNotConnected.append(accountId)
                            self.logger.info(
                                f"User {user.name} not connected to TDAmeritrade.")
                            continue

                        self.usersToTrade[accountId] = Trader(
                            tda, user, self.logger)

                        self.logger.info(f"User {user.name} ready to trade.")

                        time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error setting up user {user.name}: {e}")

    def runTrader(self):
        orders = self.gmail.getEmails()

        for user in self.usersToTrade:
            trader: Trader = self.usersToTrade[user]
            trader.trade(orders)


if __name__ == "__main__":

    main = Main()

    main.setupUsers()

    # Database().addUser(User(
    #     clientId=123456789,
    #     accounts={
    #         '123456789': 'ABC123',
    #     },
    #     name='John Doe',
    #     username='jdoe123',
    #     password='password123',
    # ))

    # TODO run on a loop
    while True:
        main.runTrader()
        time.sleep(1)
        print("--------------------------------------------------")
