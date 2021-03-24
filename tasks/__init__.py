
from datetime import datetime, timedelta
import pytz
import time
from assets.exception_handler import exception_handler
from assets.current_datetime import getDatetime


class Tasks:

    def __init__(self):

        self.balance_history = self.mongo.balance_history

        self.open_positions_history = self.mongo.open_positions_history

        self.closed_positions_history = self.mongo.closed_positions_history

        self.open_positions = self.mongo.open_positions

        self.closed_positions = self.mongo.closed_positions

        self.strategy_history = self.mongo.strategy_history

        self.logger = self.logger

        self.alert_sent = []

        self.inconsistent_list = []

        self.market_close_check = False

        self.midnight = False

        self.on_the_hour = False

        self.isAlive = True

        self.market_close_check = False

        self.eleven_check = False

    @exception_handler
    def updateAccountBalance(self):
        """ METHOD UPDATES USERS ACCOUNT BALANCE IN MONGODB
        """
        account = self.tdameritrade.getAccount()

        liquidation_value = float(
            account["securitiesAccount"]["currentBalances"]["liquidationValue"])

        available_for_trading = float(
            account["securitiesAccount"]["currentBalances"]["cashAvailableForTrading"])

        self.users.update_one({"Name": self.user["Name"]}, {"$set": {
                                f"Accounts.{self.account_id}.Account_Balance": liquidation_value, f"Accounts.{self.account_id}.Available_For_Trading": available_for_trading}})

    @exception_handler
    def updateLastPrice(self):
        """ METHOD UPDATES LAST PRICE FOR EACH SYMBOL IN OPEN POSITIONS/QUEUED
        """
        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(
            pytz.timezone('US/Central')).strftime("%H:%M")

        # UPDATE POSITION LAST PRICE AND UPDATE HIGH PRICE
        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        open_positions_list = []

        for position in open_positions:

            symbol = position["Symbol"]

            if symbol not in open_positions_list:

                open_positions_list.append(symbol)

        if len(open_positions_list) > 0:

            resp = self.tdameritrade.getQuotes(open_positions_list)

            if resp:

                for key, value in resp.items():

                    symbol = key

                    last_price = value["lastPrice"]

                    self.open_positions.update_many({"Trader": self.user["Name"], "Symbol": symbol, "Asset_Type": self.asset_type, "Account_ID": self.account_id}, {
                                                    "$set": {"Last_Price": last_price}})

                    if dt_central == "15:00":

                        self.open_positions.update_many({"Trader": self.user["Name"], "Symbol": symbol, "Asset_Type": self.asset_type, "Account_ID": self.account_id}, {
                                                        "$set": {"Opening_Price": last_price}})

        # UPDATE QUEUE LAST PRICE
        queues = self.queue.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type})

        queues_list = []

        for queue in queues:

            if self.asset_type == "EQUITY":

                symbol = queue["Symbol"]

            elif self.asset_type == "OPTION":

                symbol = queue["Pre_Symbol"]

            if symbol not in queues_list:

                queues_list.append(symbol)

        if len(queues_list) > 0:

            resp = self.tdameritrade.getQuotes(queues_list)

            for key, value in resp.items():

                symbol = key

                last_price = value["lastPrice"]

                if self.asset_type == "EQUITY":

                    self.queue.update_many({"Trader": self.user["Name"], "Symbol": symbol, "Asset_Type": self.asset_type, "Account_ID": self.account_id}, {
                                            "$set": {"Last_Price": last_price}})

                elif self.asset_type == "OPTION":

                    self.queue.update_many({"Trader": self.user["Name"], "Pre_Symbol": symbol, "Asset_Type": self.asset_type, "Account_ID": self.account_id}, {
                                            "$set": {"Last_Price": last_price}})

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

        available_for_trading = self.user["Accounts"][self.account_id]["Available_For_Trading"]

        # GET CURRENT BALANCE
        balance_found = self.balance_history.find_one(
            {"Date":  dt_only, "Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        profit_loss = 0

        closed_positions = self.closed_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})
        
        for position in closed_positions:

            buy_price = position["Buy_Price"]

            sell_price = position["Sell_Price"]

            qty = position["Qty"]

            profit_loss += ((sell_price * qty) - (buy_price * qty))

        if not balance_found:
            
            self.balance_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Asset_Type": self.asset_type,
                "Account_ID": self.account_id,
                "Balance": balance,
                "Available_For_Trading": available_for_trading,
                "Profit_Loss": profit_loss
            })

    @exception_handler
    def openPositionHistory(self):
        """ METHOD SAVES OPEN POSITION HISTORY (PROFIT LOSS) AT THE END OF DAY
        """
        dt_only, tm_only = self.getDatetimeSplit()

        # GET OPEN POSITIONS
        open_positions_found = self.open_positions_history.find_one(
            {"Date": dt_only, "Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        obj = {}

        for position in open_positions:

            strategy = position["Strategy"]

            buy_price = position["Buy_Price"]

            last_price = position["Last_Price"]

            qty = position["Qty"]

            change = (last_price * qty) - (buy_price * qty)

            if strategy not in obj:

                obj[strategy] = {"chng": 0}

            obj[strategy]["chng"] += change

        if not open_positions_found:

            self.open_positions_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Asset_Type": self.asset_type,
                "Account_ID": self.account_id,
                "Open_Position_Strategies": obj
            })

    @exception_handler
    def closedPositionHistory(self):
        """ METHOD SAVES CLOSED POSITIONS HISTORY (PROFIT LOSS) AT END OF DAY
        """
        dt_only, tm_only = self.getDatetimeSplit()

        # GET CURRENT POSITIONS COUNT
        closed_positions_found = self.closed_positions_history.find_one(
            {"Date": dt_only, "Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        closed_positions = self.closed_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        obj = {}

        for position in closed_positions:

            strategy = position["Strategy"]

            buy_price = position["Buy_Price"]

            sell_price = position["Sell_Price"]

            qty = position["Qty"]

            change = (sell_price * qty) - (buy_price * qty)

            if strategy not in obj:

                obj[strategy] = {"chng": 0}

            obj[strategy]["chng"] += change

        if not closed_positions_found:

            self.closed_positions_history.insert_one({
                "Trader": self.user["Name"],
                "Date": dt_only,
                "Asset_Type": self.asset_type,
                "Account_ID": self.account_id,
                "Closed_Position_Strategies": obj
            })

    # KILL QUEUE ORDER IF SITTING IN QUEUE GREATER THAN 2 HOURS
    @exception_handler
    def killQueueOrder(self):
        """ METHOD QUERIES ORDERS IN QUEUE AND LOOKS AT INSERTION TIME.
            IF QUEUE ORDER INSERTION TIME GREATER THAN TWO HOURS, THEN THE ORDER IS CANCELLED.
        """
        # CHECK ALL QUEUE ORDERS AND CANCEL ORDER IF GREATER THAN TWO HOURS OLD
        queue_orders = self.queue.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

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
                        "Aggregation": order["Aggregation"],
                        "Trader": self.user["Name"],
                        "Date": getDatetime()
                    }

                    if self.asset_type == "OPTION":

                        other["Pre_Symbol"] = order["Pre_Symbol"]

                        other["Exp_Date"] = order["Exp_Date"]

                    self.other.insert_one(other)

                    self.queue.delete_one(
                        {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"], "Asset_Type": self.asset_type})

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
    
    # SELL OUT MARKET OPEN IF SELL ORDERS IN QUEUE
    @exception_handler
    def sellAtMarketOpen(self):
        """ METHOD CHECKS QUEUE FOR SELL ORDERS, CANCELS THOSE ORDERS, AND RESELLS AT MARKET OPEN WITH MARKET ORDER
        """

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        day = dt_central.strftime("%a")

        tm = dt_central.strftime("%H:%M:%S")

        weekdays = ["Sat", "Sun"]

        # CHECK IF MARKET OPEN AND NOT WEEKEND
        if tm == "08:30"  and day not in weekdays:

            queue_orders = self.mongo.queue.find(
                {"Trader": self.user["Name"], "Account_ID": self.account_id, "Order_Type" : "SELL"})

            for order in queue_orders:

                # CANCEL ORDER
                resp = self.tdameritrade.cancelOrder(order["Order_ID"])

                if resp.status_code == 200 or resp.status_code == 201:

                    trade_data = {
                        "Symbol": order["Symbol"],
                        "Side": "SELL",
                        "Aggregation": order["Aggregation"],
                        "Strategy": order["Strategy"],
                        "Asset_Type": order["Asset_Type"],
                        "Account_ID": self.account_id
                    }

                    # SELL MARKET ORDER
                    self.placeOrder(trade_data, order, orderType="MARKET")

    # SELL END OF DAY STOCK
    @exception_handler
    def sellOutStrategies(self, strategies):
        """ METHOD SELLS OUT ANY OPEN POSITIONS THAT HAVE A PARTICULAR STRATEGY.

        Args:
            strategies ([list]): LIST OF STRATEGIES.
        """

        # GET ALL SECONDARY_AGG POSITIONS AND SELL THEM
        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "$or": strategies, "Asset_Type": self.asset_type, "Account_ID" : self.account_id})

        for position in open_positions:

            trade_data = {
                "Symbol": position["Symbol"],
                "Side": "SELL",
                "Aggregation": position["Aggregation"],
                "Strategy": position["Strategy"],
                "Asset_Type": position["Asset_Type"],
                "Account_ID": self.account_id
            }

            queued = self.queue.find_one(
                {"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"], "Asset_Type": position["Asset_Type"], "Account_ID" : self.account_id})

            if not queued:

                self.placeOrder(trade_data, position, orderType="MARKET")

    # SELL ALL STOCK
    @exception_handler
    def sellOutAllStock(self):
        """ METHOD SELLS OUT ALL OPEN POSITIONS. THIS IS IN CASE OF CATASTROPHIC FAILURE OR STOCK MARKET CRASH.
        """
        # GET ALL POSITIONS FOR ACCOUNT
        open_positions = self.open_positions.find({"Trader": self.user["Name"], "Asset_Type" : self.asset_type, "Account_ID" : self.account_id})

        for position in open_positions:

            trade_data = {
                "Symbol": position["Symbol"],
                "Side": "SELL",
                "Aggregation": position["Aggregation"],
                "Strategy": position["Strategy"],
                "Asset_Type": position["Asset_Type"],
                "Account_ID": self.account_id
            }

            queued = self.queue.find_one(
                {"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"], "Asset_Type": position["Asset_Type"], "Account_ID" : self.account_id})

            if not queued:

                self.placeOrder(trade_data, position, orderType="MARKET")

    # SELL OUT OF OPTIONS IF EXP DATE REACHED
    @exception_handler
    def sellOutOptions(self):
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
                    "Aggregation": position["Aggregation"],
                    "Strategy": position["Strategy"],
                    "Asset_Type": position["Asset_Type"],
                    "Exp_Date": position["Exp_Date"]
                }

                self.placeOrder(trade_data, position)

    # CHECKS IF PRICE HAS DROPPED 5% OF HIGH
    @exception_handler
    def checkTrailingStop(self):
        """ METHOD CHECKS TO SEE IF LAST PRICE OF STOCK HAS DROPPED 5% OF HIGHEST PRICE OF STOCK SINCE BUY.
            IF DROP BELOW 5%, THEN THE POSITION SELLS.
        """
        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Asset_Type": self.asset_type, "Account_ID": self.account_id})

        for position in open_positions:

            last_price = position["Last_Price"]

            high_price = position["High_Price"]

            five_percent = round(high_price * 0.95, 2)

            if last_price > high_price:

                self.open_positions.update_one({"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"], "Asset_Type": self.asset_type}, {
                                                "$set": {"High_Price": last_price}})

            # CHECK IF LAST PRICE < 5% OF HIGH PRICE
            elif last_price < five_percent and self.user["Accounts"][self.account_id]["Trailing_Stop_Active"]:

                queued = self.queue.find_one(
                    {"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"], "Asset_Type": self.asset_type})

                # IF TRUE AND NOT IN QUEUE, SELL OUT POSITION
                if not queued:

                    trade_data = {
                        "Symbol": position["Symbol"],
                        "Aggregation": position["Aggregation"],
                        "Strategy": position["Strategy"],
                        "Asset_Type": position["Asset_Type"],
                        "Account_ID": self.account_id
                    }

                    trade_data["Side"] = "SELL"

                    if self.asset_type == "OPTION":

                        trade_data["Exp_Date"] = position["Exp_Date"]

                        trade_data["Pre_Symbol"] = position["Pre_Symbol"]

                        trade_data["Side"] = "SELL_TO_CLOSE"

                    self.placeOrder(trade_data, position)

                    msg = f"Symbol {position['Symbol']} is selling due to 5% drop of high price - TRADER: {self.user['Name']}"

                    self.logger.INFO(msg)

    # ADD NEW STRATEGIES TO OBJECT
    @exception_handler
    def updateStrategiesObject(self, strategy):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        # IF STRATEGY DOESNT EXIST IN OBJECT, THEN ADD IT AND SET DEFAULT TO 1 SHARE AD ACTIVE
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

                self.user = self.users.find_one({"Name": self.user["Name"]})

                self.asset_type = self.user["Accounts"][self.account_id]["Asset_Type"]

                self.updateAccountBalance()

                self.updateLastPrice()

                dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

                dt_central = dt.astimezone(pytz.timezone('US/Central'))

                # IF MIDNIGHT, ADD BALANCE, OPEN POSITIONS PROFIT/LOSS, CLOSED POSITIONS PROFIT/LOSS.
                midnight = dt_central.time().strftime("%H:%M")

                if midnight == "23:55":

                    if not self.midnight:

                        self.balanceHistory()

                        self.openPositionHistory()

                        self.closedPositionHistory()

                        self.midnight = True

                else:

                    self.midnight = False

                # RUN TASKS ####################################################

                if self.asset_type == "OPTION":

                    self.sellOutOptions()

                self.checkTrailingStop()

                self.killQueueOrder()

                self.sellAtMarketOpen()

                dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

                dt_central = dt.astimezone(pytz.timezone('US/Central'))

                # SELL ALL SECONDARY_AGG, SEC_AGG_V2 POSITIONS AT END OF DAY
                if dt_central.strftime("%H:%M") == "14:55" and self.asset_type == "EQUITY":

                    if not self.market_close_check:

                        self.sellOutStrategies([{"Strategy": "Secondary_Agg"},
                                        {"Strategy": "Sec_Agg_v2"}])

                        self.market_close_check = True

                else:

                    self.market_close_check = False

                # SELL ALL Sec_Agg_Daytrade AT 14:30
                if dt_central.strftime("%H:%M") == "14:30" and self.asset_type == "EQUITY":

                    if not self.eleven_check:

                        self.sellOutStrategies([{"Strategy": "Sec_Aggressive"}])

                        self.eleven_check = True

                else:

                    self.eleven_check = False

            except KeyError:

                self.isAlive = False

            except Exception:

                self.logger.ERROR(
                    f"ACCOUNT ID: {self.account_id} - TRADER: {self.user['Name']}")

            finally:

                time.sleep(selectSleep())

        self.logger.INFO(f"TASK STOPPED FOR ACCOUNT ID {self.account_id}")
