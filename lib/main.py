

import time
from src.services.tda import TDA
from src.models.user_model import User
from src.services.database import Database
from src.services.gmail import Gmail
from src.trader import Trader


class Main(Database):

    def __init__(self) -> None:
        super().__init__()
        self.gmail = Gmail()
        self.usersToTrade = {}
        self.usersNotConnected = []

    def setupUsers(self):

        users = self.getUsers()
        print(f"Setting up {len(users)} user(s)...")
        for user in users:
            user: User = user
            try:
                for accountId in user.accounts.keys():
                    if accountId not in self.usersToTrade and accountId not in self.usersNotConnected:
                        tda = TDA(accountId, user.accounts[accountId])
                        connected = tda.connect()

                        if not connected:
                            self.usersNotConnected.append(accountId)
                            continue

                        self.usersToTrade[accountId] = Trader(tda, user)

                        time.sleep(0.1)

            except Exception as e:
                print(f"Error setting up user {user.name}: {e}")

    def runTrader(self):
        orders = self.gmail.getEmails()

        for user in self.usersToTrade:
            trader: Trader = self.usersToTrade[user]
            print(f"User {trader.tda.accountId} trading...")
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
    main.runTrader()
