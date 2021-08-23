# imports
import pytz
from datetime import datetime
import time
from live_trader import LiveTrader
from sim_trader import SimTrader
from gmail import Gmail
from mongo import MongoDB
import os
from assets.push_notification import PushNotification
from assets.logger import Logger
from tdameritrade import TDAmeritrade
from assets.exception_handler import exception_handler
from pprint import pprint

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

assets = os.path.join(THIS_FOLDER, 'assets')

class Main:

    def connectAll(self):
        """ METHOD INITIALIZES LOGGER, MONGO, GMAIL, EXCEPTION HOOK, ECT.
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

            # SET GMAIL AND MONGO ATTRIBUTE FOR LOGGER
            self.logger.gmail = self.gmail

            self.logger.mongo = self.mongo

            self.traders = {}

            self.accounts = []

            self.sim_trader = SimTrader(self.mongo)

            self.not_connected = []

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

                for account_id, info in user["Accounts"].items():

                    if account_id not in self.traders and account_id not in self.not_connected:

                        tdameritrade = TDAmeritrade(self.mongo, user, account_id, self.logger)

                        connected = tdameritrade.initialConnect()
                        
                        if connected:
                            
                            obj = LiveTrader(user, self.mongo, PushNotification(
                                user["deviceID"], self.logger, self.gmail), self.logger, int(account_id), tdameritrade)

                            self.traders[account_id] = obj

                            time.sleep(0.1)

                        else:

                            self.not_connected.append(account_id)

                    self.accounts.append(account_id)

        except Exception:

            self.logger.ERROR()

    @exception_handler
    def checkTradersAndAccounts(self):
        """ METHOD COMPARES THE CURRENT TOTAL TRADERS TO CURRENT TOTAL ACCOUNTS IN MONGO.
            IF CURRENT TRADERS > CURRENT ACCOUNTS, MEANING AN ACCOUNT WAS REMOVED, THEN REMOVE THAT INSTANCE FROM SELF.TRADERS DICT

        """

        if len(self.traders) > len(self.accounts):

            self.logger.INFO(
                f"CURRENT TOTAL TRADERS: {len(self.traders)} - CURRENT TOTAL ACCOUNTS: {len(self.accounts)}")

            accounts_to_remove = self.traders.keys() - set(self.accounts)

            for account in accounts_to_remove:

                self.traders[account].isAlive = False

                del self.traders[account]

                self.logger.INFO(f"ACCOUNT ID {account} REMOVED")

            self.accounts.clear()

    @exception_handler
    def terminateNeeded(self):

        """ METHOD ITERATES THROUGH INSTANCES AND FIND ATTRIBUTE NAMED TERMINATE AND CHECKS IF TRUE.
            IF TRUE, REMOVE FROM SELF.TRADERS AND STOP TASKS
        """

        traders = self.traders.copy()

        for account_id, info in traders.items():

            if info.tdameritrade.terminate:

                info.isAlive = False

                del self.traders[account_id]

                self.logger.INFO(f"ACCOUNT ID {account_id} REMOVED")
   
    @exception_handler
    def run(self):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """

        sim_went = False
        
        self.setupTraders()
        
        self.checkTradersAndAccounts()
        
        self.terminateNeeded()
        
        trade_data = self.gmail.getEmails()
        
        for live_trader in self.traders.values():
                
            live_trader.runTrader(trade_data)

            if not sim_went: # ONLY RUN ONCE DESPITE NUMBER OF INSTANCES

                self.sim_trader.runTrader(trade_data, live_trader.tdameritrade)

                sim_went = True
    
if __name__ == "__main__":
    """ START OF SCRIPT.
        INITIALIZES MAIN CLASS AND RUNS RUN METHOD ON WHILE LOOP WITH A SLEEP TIME THAT VARIES FROM 5 SECONDS TO 60 SECONDS.
    """

    def selectSleep():
        """
        PRE-MARKET(0400 - 0930 ET): 5 SECONDS
        MARKET OPEN(0930 - 1600 ET): 5 SECONDS
        AFTER MARKET(1600 - 2000 ET): 5 SECONDS

        WEEKENDS: 60 SECONDS
        WEEKDAYS(2000 - 0400 ET): 60 SECONDS

        EVERYTHING WILL BE BASED OFF CENTRAL TIME

        OBJECTIVE IS TO FREE UP UNNECESSARY SERVER USAGE
        """

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        day = dt_central.strftime("%a")

        tm = dt_central.strftime("%H:%M:%S")

        weekdays = ["Sat", "Sun"]

        # IF CURRENT TIME GREATER THAN 8PM AND LESS THAN 4AM, OR DAY IS WEEKEND, THEN RETURN 60 SECONDS
        if tm > "20:00" or tm < "04:00" or day in weekdays:

            return 60

        # ELSE RETURN 5 SECONDS
        return 5

    main = Main()

    connected = main.connectAll()

    if connected:

        while True:

            main.run()
            
            time.sleep(selectSleep())