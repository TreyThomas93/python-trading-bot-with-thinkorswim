
from datetime import datetime, timedelta
import pytz
import time
from assets.exception_handler import exception_handler
from assets.helper_functions import getDatetime, selectSleep, modifiedAccountID


class Tasks:

    def __init__(self):

        self.balance_history = self.mongo.balance_history

        self.profit_loss_history = self.mongo.profit_loss_history

        self.logger = self.logger

        self.market_close = False

        self.check_options = False

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

        balance = self.user["Accounts"][str(
            self.account_id)]["Account_Balance"]

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

        profit_loss_found = self.profit_loss_history.find_one(
            {"Date":  dt_only, "Trader": self.user["Name"], "Account_ID": self.account_id})

        profit_loss = 0

        closed_positions = self.closed_positions.find(
            {"Trader": self.user["Name"], "Account_ID": self.account_id})

        for position in closed_positions:

            sell_date = position["Sell_Date"].strftime("%Y-%m-%d")

            if sell_date == dt_only:

                buy_price = position["Buy_Price"]

                sell_price = position["Sell_Price"]

                qty = position["Qty"]

                profit_loss += ((sell_price * qty) - (buy_price * qty))

        if not profit_loss_found:

            self.profit_loss_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Account_ID": self.account_id,
                "Profit_Loss": profit_loss
            })

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

    @exception_handler
    def sellOptionsAtExpiration(self):
        """ METHOD SELLS OUT OPTIONS IF ONE DAY BEFORE EXPIRATION
        """

        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": "OPTION"})

        dt = getDatetime()

        for position in open_positions:

            day_before = (position["Exp_Date"] -
                          timedelta(days=1)).strftime("%Y-%m-%d")

            if day_before == dt.strftime("%Y-%m-%d"):

                trade_data = {
                    "Symbol": position["Symbol"],
                    "Pre_Symbol": position["Pre_Symbol"],
                    "Side": "SELL_TO_CLOSE",
                    "Option_Type": position["Option_Type"],
                    "Strategy": position["Strategy"],
                    "Asset_Type": position["Asset_Type"],
                    "Exp_Date": position["Exp_Date"]
                }

                self.placeOrder(trade_data, position)

    @ exception_handler
    def updateStrategiesObject(self, strategy, asset_type):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        obj = {"Active": True,
               "Order_Type": "Standard",
               "Asset_Type": asset_type,
               "Position_Size": 500,
               }

        # IF STRATEGY DOESNT EXIST IN OBJECT, THEN ADD STRATEGY OBJ ABOVE
        self.users.update(
            {"Name": self.user["Name"], f"Accounts.{self.account_id}.Strategies.{strategy}": {"$exists": False}}, {
                "$set": {f"Accounts.{self.account_id}.Strategies.{strategy}": obj}}
        )

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.INFO(
            f"STARTING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})\n")

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                self.killQueueOrder()

                self.updateAccountBalance()

                tm = getDatetime().time().strftime("%H:%M")

                if tm == "08:30":  # set this based on YOUR timezone

                    if not self.check_options:

                        self.sellOptionsAtExpiration()

                        self.check_options = True

                else:

                    self.check_options = False

                # IF MARKET CLOSE, ADD BALANCE, PROFIT/LOSS TO HISTORY
                if tm == "16:00":

                    if not self.market_close:

                        self.balanceHistory()

                        self.profitLossHistory()

                        self.market_close = True

                else:

                    self.midnight = False

            except KeyError:

                self.isAlive = False

            except Exception:

                self.logger.ERROR(
                    f"ACCOUNT ID: {modifiedAccountID(self.account_id)} - TRADER: {self.user['Name']}")

            finally:

                time.sleep(selectSleep())

        self.logger.INFO(
            f"TASK STOPPED FOR ACCOUNT ID {modifiedAccountID(self.account_id)}")
