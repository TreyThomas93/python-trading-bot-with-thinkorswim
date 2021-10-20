# imports
import time
from live_trader import LiveTrader
from paper_trader import PaperTrader
from gmail import Gmail
from mongo import MongoDB
import os
from assets.push_notification import PushNotification
from assets.logger import Logger
from tdameritrade import TDAmeritrade
from assets.exception_handler import exception_handler
from assets.helper_functions import selectSleep

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

assets = os.path.join(THIS_FOLDER, 'assets')


class Main:

    def connectAll(self):
        """ METHOD INITIALIZES LOGGER, MONGO, GMAIL, PAPERTRADER.
        """

        # INSTANTIATE LOGGER
        self.logger = Logger()

        # CONNECT TO MONGO
        self.mongo = MongoDB(self.logger)

        mongo_connected = self.mongo.connect()

        # CONNECT TO GMAIL API
        self.gmail = Gmail(self.logger)

        gmail_connected = self.gmail.connect()

        if mongo_connected and gmail_connected:

            self.traders = {}

            self.accounts = []

            self.paper_trader = PaperTrader(self.mongo)

            self.not_connected = []

            # SET TO TRUE TO LIVE TRADE/FALSE TO STOP LIVE TRADING
            self.live_trader_active = False

            return True

        return False

    @exception_handler
    def setupTraders(self):
        """ METHOD GETS ALL USERS ACCOUNTS FROM MONGO AND CREATES LIVE TRADER INSTANCES FOR THOSE ACCOUNTS.
            IF ACCOUNT INSTANCE ALREADY IN SELF.TRADERS DICT, THEN ACCOUNT INSTANCE WILL NOT BE CREATED AGAIN.
        """
        try:

            # GET ALL USERS ACCOUNTS
            users = self.mongo.users.find({})

            for user in users:

                for account_id in user["Accounts"].keys():

                    if account_id not in self.traders and account_id not in self.not_connected:

                        push_notification = PushNotification(
                            user["deviceID"], self.logger, self.gmail)

                        tdameritrade = TDAmeritrade(
                            self.mongo, user, account_id, self.logger, push_notification)

                        connected = tdameritrade.initialConnect()

                        if connected:

                            obj = LiveTrader(user, self.mongo, push_notification, self.logger, int(
                                account_id), tdameritrade)

                            self.traders[account_id] = obj

                            time.sleep(0.1)

                        else:

                            self.not_connected.append(account_id)

                    self.accounts.append(account_id)

        except Exception:

            self.logger.ERROR()

    @exception_handler
    def run(self):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """

        paper_went = False

        self.setupTraders()

        trade_data = self.gmail.getEmails()

        for live_trader in self.traders.values():

            if self.live__trader_active:

                live_trader.runTrader(trade_data)

            if not paper_went:  # ONLY RUN ONCE DESPITE NUMBER OF INSTANCES

                self.paper_trader.runTrader(
                    trade_data, live_trader.tdameritrade)

                paper_went = True


if __name__ == "__main__":
    """ START OF SCRIPT.
        INITIALIZES MAIN CLASS AND STARTS RUN METHOD ON WHILE LOOP WITH A DYNAMIC SLEEP TIME.
    """

    main = Main()

    connected = main.connectAll()

    if connected:

        main.logger.INFO(
            f"LIVE TRADER IS {'ACTIVE' if main.live_trader_active else 'INACTIVE'}\n")

        while True:

            main.run()

            time.sleep(selectSleep())
