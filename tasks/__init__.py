
from datetime import datetime, timedelta
import pytz
import time
from assets.exception_handler import exception_handler
from assets.current_datetime import getDatetime


class Tasks:

    def __init__(self):

        self.balance_history = self.mongo.balance_history

        self.profit_loss_history = self.mongo.profit_loss_history

        self.logger = self.logger
        
        self.midnight = False

        self.isAlive = True

    @exception_handler
    def updateAccountBalance(self):
        """ METHOD UPDATES USERS ACCOUNT BALANCE IN MONGODB
        """
        account = self.tdameritrade.getAccount()

        liquidation_value = float(
            account["securitiesAccount"]["currentBalances"]["liquidationValue"])

        self.users.update_one({"Name": self.user["Name"]}, {"$set": {
            f"Accounts.{self.account_id}.Account_Balance": liquidation_value}})

    @exception_handler
    def getDatetimeSplit(self):

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        dt = datetime.strftime(dt_central, "%Y-%m-%d %H:00")

        dt_only = dt.split(" ")[0].strip()

        tm_only = dt.split(" ")[1].strip()

        return (dt_only, tm_only)

    @exception_handler
    def balanceHistory(self):
        """ METHOD SAVES BALANCE HISTORY AT THE END OF THE DAY
        """
        dt_only, tm_only = self.getDatetimeSplit()

        balance = self.user["Accounts"][self.account_id]["Account_Balance"]

        # GET CURRENT BALANCE
        balance_found = self.balance_history.find_one(
            {"Date":  dt_only, "Trader": self.user["Name"], "Account_ID": self.account_id})

        if not balance_found:

            self.balance_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Account_ID": self.account_id,
                "Balance": balance
            })

    @exception_handler
    def profitLossHistory(self):

        dt_only, tm_only = self.getDatetimeSplit()

        profit_loss_found = self.balance_history.find_one(
            {"Date":  dt_only, "Trader": self.user["Name"], "Account_ID": self.account_id})

        profit_loss = 0

        closed_positions = self.closed_positions.find(
            {"Trader": self.user["Name"], "Account_ID": self.account_id})

        for position in closed_positions:

            buy_price = position["Buy_Price"]

            sell_price = position["Sell_Price"]

            qty = position["Qty"]

            profit_loss += ((sell_price * qty) - (buy_price * qty))

        if not profit_loss_found:

            self.balance_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Account_ID": self.account_id,
                "Profit_Loss": profit_loss
            })

    # KILL QUEUE ORDER IF SITTING IN QUEUE GREATER THAN 2 HOURS
    @ exception_handler
    def killQueueOrder(self):
        """ METHOD QUERIES ORDERS IN QUEUE AND LOOKS AT INSERTION TIME.
            IF QUEUE ORDER INSERTION TIME GREATER THAN TWO HOURS, THEN THE ORDER IS CANCELLED.
        """
        # CHECK ALL QUEUE ORDERS AND CANCEL ORDER IF GREATER THAN TWO HOURS OLD
        queue_orders = self.queue.find(
            {"Trader": self.user["Name"], "Account_ID": self.account_id})

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        two_hours_ago = datetime.strptime(datetime.strftime(
            dt_central - timedelta(hours=2), "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        ten_minutes_ago = datetime.strptime(datetime.strftime(
            dt_central - timedelta(minutes=10), "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        for order in queue_orders:

            order_date = order["Date"]

            order_type = order["Order_Type"]

            id = order["Order_ID"]

            forbidden = ["REJECTED", "CANCELED", "FILLED"]

            if two_hours_ago > order_date and (order_type == "BUY" or order_type == "BUY_TO_OPEN") and id != None and order["Order_Status"] not in forbidden:

                # FIRST CANCEL ORDER
                resp = self.tdameritrade.cancelOrder(id)

                if resp.status_code == 200 or resp.status_code == 201:

                    other = {
                        "Symbol": order["Symbol"],
                        "Order_Type": order["Order_Type"],
                        "Order_Status": "CANCELED",
                        "Strategy": order["Strategy"],
                        "Account_ID": self.account_id,
                        "Trader": self.user["Name"],
                        "Date": getDatetime()
                    }

                    self.other.insert_one(other)

                    self.queue.delete_one(
                        {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]})

                    self.logger.INFO(
                        f"CANCELED ORDER FOR {order['Symbol']} - TRADER: {self.user['Name']}", True)

            # IF QUEUE ORDER DATE GREATER THAN 10 MINUTES OLD AND ORDER ID EQUALS NONE, SEND ALERT
            if ten_minutes_ago > order_date and order["Order_ID"] == None and order["Account_ID"] == self.account_id:

                if order["Symbol"] not in self.no_ids_list:

                    self.logger.ERROR(
                        "QUEUE ORDER ID ERROR", f"ORDER ID FOR {order['Symbol']} NOT FOUND - TRADER: {self.user['Name']} - ACCOUNT ID: {self.account_id}")

                    self.no_ids_list.append(order["Symbol"])

            else:

                if order["Symbol"] in self.no_ids_list:

                    self.no_ids_list.remove(order["Symbol"])

    # ADD NEW STRATEGIES TO OBJECT
    @ exception_handler
    def updateStrategiesObject(self, strategy):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        # IF STRATEGY DOESNT EXIST IN OBJECT, THEN ADD IT AND SET DEFAULT TO 1 SHARE AND ACTIVE STATUS
        self.users.update(
            {"Name": self.user["Name"], f"Accounts.{self.account_id}.Strategies.{strategy}": {"$exists": False}}, {
                "$set": {f"Accounts.{self.account_id}.Strategies.{strategy}": {"Shares": 1, "Active": True}}}
        )

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.INFO(
            f"STARTING TASKS FOR TRADER {self.user['Name']} - ACCOUNT ID: {self.account_id}\n")

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

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                self.killQueueOrder()

                self.updateAccountBalance()

                dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

                dt_central = dt.astimezone(pytz.timezone('US/Central'))

                # IF MIDNIGHT, ADD BALANCE, PROFIT/LOSS TO HISTORY
                midnight = dt_central.time().strftime("%H:%M")

                if midnight == "23:55":

                    if not self.midnight:

                        self.balanceHistory()

                        self.profitLossHistory()

                        self.midnight = True

                else:

                    self.midnight = False

            except KeyError:

                self.isAlive = False

            except Exception:

                self.logger.ERROR(
                    f"ACCOUNT ID: {self.account_id} - TRADER: {self.user['Name']}")

            finally:

                time.sleep(selectSleep())

        self.logger.INFO(f"TASK STOPPED FOR ACCOUNT ID {self.account_id}")
