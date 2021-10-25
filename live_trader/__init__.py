from assets.helper_functions import getDatetime, modifiedAccountID
from live_trader.tasks import Tasks
from threading import Thread
from assets.exception_handler import exception_handler
from live_trader.order_builder import OrderBuilder
from dotenv import load_dotenv
from pathlib import Path
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

RUN_TASKS = True if os.getenv('RUN_TASKS') == "True" else False


class LiveTrader(Tasks, OrderBuilder):

    def __init__(self, user, mongo, push, logger, account_id, tdameritrade):
        """
        Args:
            user ([dict]): [USER DATA FOR CURRENT INSTANCE]
            mongo ([object]): [MONGO OBJECT CONNECTING TO DB]
            push ([object]): [PUSH OBJECT FOR PUSH NOTIFICATIONS]
            logger ([object]): [LOGGER OBJECT FOR LOGGING]
            account_id ([str]): [USER ACCOUNT ID FOR TDAMERITRADE]
            asset_type ([str]): [ACCOUNT ASSET TYPE (EQUITY, OPTIONS)]
        """
        self.tdameritrade = tdameritrade

        self.mongo = mongo

        self.account_id = account_id

        self.user = user

        self.users = mongo.users

        self.push = push

        self.open_positions = mongo.open_positions

        self.closed_positions = mongo.closed_positions

        self.strategies = mongo.strategies

        self.rejected = mongo.rejected

        self.canceled = mongo.canceled

        self.queue = mongo.queue

        self.logger = logger

        self.no_ids_list = []

        OrderBuilder.__init__(self)

        Tasks.__init__(self)

        # If user wants to run tasks and there are more than two methods (outside of runTasks and addNewStrategy) found, indicating post production tasks were found.
        if RUN_TASKS and len([i for i in dir(Tasks) if "_" not in i]) > 2:

            Thread(target=self.runTasks, daemon=True).start()

        else:

            self.logger.INFO(
                f"NOT RUNNING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})\n")

    # STEP ONE
    @exception_handler
    def sendOrder(self, trade_data, strategy_object, direction):

        from pprint import pprint

        order_type = strategy_object["Order_Type"]

        if order_type == "STANDARD":

            order, obj = self.standardOrder(
                trade_data, strategy_object, direction)

        elif order_type == "OCO":

            order, obj = self.OCOorder(trade_data, strategy_object, direction)

        pprint(obj)
        print("\n")
        pprint(order)


      # PLACE ORDER ################################################
      # resp = self.tdameritrade.placeTDAOrder(order)

      # status_code = resp.status_code

      # if status_code not in [200, 201]:

      #     other = {
      #         "Symbol": symbol,
      #         "Order_Type": side,
      #         "Order_Status": "REJECTED",
      #         "Strategy": strategy,
      #         "Trader": self.user["Name"],
      #         "Date": getDatetime(),
      #         "Account_ID": self.account_id
      #     }

      #     self.logger.INFO(
      #         f"{symbol} REJECTED For {self.user['Name']} - REASON: {(resp.json())['error']}", True)

      #     self.rejected.insert_one(other)

      #     return

      # # GETS ORDER ID FROM RESPONSE HEADERS LOCATION
      # obj["Order_ID"] = int(
      #     (resp.headers["Location"]).split("/")[-1].strip())

      # obj["Order_Status"] = "QUEUED"

      # self.queueOrder(obj)

      # response_msg = f"{side} ORDER RESPONSE: {resp.status_code} - SYMBOL: {symbol} - TRADER: {self.user['Name']} - ACCOUNT ID: {self.account_id}"

      # self.logger.INFO(response_msg)

    # STEP TWO

    @exception_handler
    def queueOrder(self, order):
        """ METHOD FOR QUEUEING ORDER TO QUEUE COLLECTION IN MONGODB

        Args:
            order ([dict]): [ORDER DATA TO BE PLACED IN QUEUE COLLECTION]
        """
        # ADD TO QUEUE WITHOUT ORDER ID AND STATUS
        self.queue.insert_one(order)

    # STEP THREE
    @exception_handler
    def updateStatus(self):
        """ METHOD QUERIES THE QUEUED ORDERS AND USES THE ORDER ID TO QUERY TDAMERITRADES ORDERS FOR ACCOUNT TO CHECK THE ORDERS CURRENT STATUS.
            INITIALLY WHEN ORDER IS PLACED, THE ORDER STATUS ON TDAMERITRADES END IS SET TO WORKING OR QUEUED. THREE OUTCOMES THAT I AM LOOKING FOR ARE
            FILLED, CANCELED, REJECTED.

            IF FILLED, THEN QUEUED ORDER IS REMOVED FROM QUEUE AND THE pushOrder METHOD IS CALLED.

            IF REJECTED OR CANCELED, THEN QUEUED ORDER IS REMOVED FROM QUEUE AND SENT TO OTHER COLLECTION IN MONGODB.

            IF ORDER ID NOT FOUND, THEN ASSUME ORDER FILLED AND MARK AS ASSUMED DATA. ELSE MARK AS RELIABLE DATA.
        """

        queued_orders = self.queue.find({"Trader": self.user["Name"], "Order_ID": {
                                        "$ne": None}, "Account_ID": self.account_id})

        for queue_order in queued_orders:

            spec_order = self.tdameritrade.getSpecificOrder(
                queue_order["Order_ID"])

            # ORDER ID NOT FOUND. ASSUME REMOVED
            if "error" in spec_order:

                side = queue_order["Order_Type"]

                position_type = queue_order["Position_Type"]

                if side == "BUY":

                    if position_type == "Long":

                        direction = "OPEN"

                    elif position_type == "Short":

                        direction = "CLOSED"

                elif side == "SELL":

                    if position_type == "Long":

                        direction = "CLOSED"

                    elif position_type == "Short":

                        direction = "OPEN"

                elif side == "BUY_TO_OPEN" or side == "SELL_TO_OPEN":

                    direction = "OPEN"

                elif side == "BUY_TO_CLOSE" or side == "SELL_TO_CLOSE":

                    direction = "CLOSED"

                self.logger.WARNING(
                    filename=__class__.__name__, warning=f"ORDER ID NOT FOUND. MOVING {queue_order['Symbol']} {queue_order['Order_Type']} ORDER TO {direction} POSITIONS")

                custom = {
                    "price": queue_order["Buy_Price"],
                    "shares": queue_order["Qty"]
                }

                data_integrity = "Assumed"

                self.pushOrder(queue_order, custom, data_integrity)

                continue

            new_status = spec_order["status"]

            order_type = queue_order["Order_Type"]

            # CHECK IF QUEUE ORDER ID EQUALS TDA ORDER ID
            if queue_order["Order_ID"] == spec_order["orderId"]:

                if new_status == "FILLED":

                    self.pushOrder(queue_order, spec_order)

                elif new_status == "CANCELED" or new_status == "REJECTED":

                    # REMOVE FROM QUEUE
                    self.queue.delete_one({"Trader": self.user["Name"], "Symbol": queue_order["Symbol"],
                                           "Strategy": queue_order["Strategy"], "Account_ID": self.account_id})

                    other = {
                        "Symbol": queue_order["Symbol"],
                        "Order_Type": order_type,
                        "Order_Status": new_status,
                        "Strategy": queue_order["Strategy"],
                        "Trader": self.user["Name"],
                        "Date": getDatetime(),
                        "Account_ID": self.account_id
                    }

                    self.rejected.insert_one(
                        other) if new_status == "REJECTED" else self.canceled.insert_one(other)

                    self.logger.INFO(
                        f"{new_status.upper()} ORDER For {queue_order['Symbol']} - TRADER: {self.user['Name']}", True)

                else:

                    self.queue.update_one({"Trader": self.user["Name"], "Symbol": queue_order["Symbol"], "Strategy": queue_order["Strategy"]}, {
                        "$set": {"Order_Status": new_status}})

    # STEP FOUR
    @exception_handler
    def pushOrder(self, queue_order, spec_order, data_integrity="Reliable"):
        """ METHOD PUSHES ORDER TO EITHER OPEN POSITIONS OR CLOSED POSITIONS COLLECTION IN MONGODB.
            IF BUY ORDER, THEN PUSHES TO OPEN POSITIONS.
            IF SELL ORDER, THEN PUSHES TO CLOSED POSITIONS.

        Args:
            queue_order ([dict]): [QUEUE ORDER DATA FROM QUEUE]
            spec_order ([dict(json)]): [ORDER DATA FROM TDAMERITRADE]
        """

        symbol = queue_order["Symbol"]

        if "orderActivityCollection" in spec_order:

            price = spec_order["orderActivityCollection"][0]["executionLegs"][0]["price"]

            shares = int(spec_order["quantity"])

        else:

            price = spec_order["price"]

            shares = int(queue_order["Qty"])

        if price < 1:

            price = round(price, 4)

        else:

            price = round(price, 2)

        strategy = queue_order["Strategy"]

        order_type = queue_order["Order_Type"]

        account_id = queue_order["Account_ID"]

        position_size = queue_order["Position_Size"]

        asset_type = queue_order["Asset_Type"]

        obj = {
            "Symbol": symbol,
            "Strategy": strategy,
            "Position_Size": position_size,
            "Data_Integrity": data_integrity,
            "Trader": self.user["Name"],
            "Account_ID": account_id,
            "Asset_Type": asset_type
        }

        if asset_type == "OPTION":

            obj["Pre_Symbol"] = queue_order["Pre_Symbol"]

            obj["Exp_Date"] = queue_order["Exp_Date"]

            obj["Option_Type"] = queue_order["Option_Type"]

        if order_type == "BUY" or order_type == "BUY_TO_OPEN":

            obj["Qty"] = shares

            obj["Buy_Price"] = price

            obj["Date"] = getDatetime()

            # ADD TO OPEN POSITIONS
            try:

                self.open_positions.insert_one(obj)

            except writeConcernError:

                self.logger.ERROR(
                    f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - writeConcernError")

                self.open_positions.insert_one(obj)

            except writeError:

                self.logger.ERROR(
                    f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - writeError")

                self.open_positions.insert_one(obj)

            except Exception:

                self.logger.ERROR()

            msg = f"____ \n Side: {order_type} \n Symbol: {symbol} \n Qty: {shares} \n Price: ${price} \n Strategy: {strategy} \n Asset Type: {asset_type} \n Date: {getDatetime()} \n Trader: {self.user['Name']} \n"

            self.logger.INFO(
                f"{order_type} ORDER For {symbol} - TRADER: {self.user['Name']}", True)

        elif order_type == "SELL" or order_type == "SELL_TO_OPEN":

            position = self.open_positions.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            obj["Qty"] = position["Qty"]

            obj["Buy_Price"] = position["Buy_Price"]

            obj["Buy_Date"] = position["Date"]

            obj["Sell_Price"] = price

            obj["Sell_Date"] = getDatetime()

            sell_price = round(price * position["Qty"], 2)

            buy_price = round(
                position["Buy_Price"] * position["Qty"], 2)

            if buy_price != 0:

                rov = round(
                    ((sell_price / buy_price) - 1) * 100, 2)

            else:

                rov = 0

            if rov > 0 or sell_price - buy_price > 0:

                sold_for = "GAIN"

            elif rov < 0 or sell_price - buy_price < 0:

                sold_for = "LOSS"

            else:

                sold_for = "NONE"

            obj["ROV"] = rov

            msg = f"____ \n Side: {order_type} \n Symbol: {symbol} \n Qty: {position['Qty']} \n Buy Price: ${position['Buy_Price']} \n Buy Date: {position['Date']} \n Sell Price: ${price} \n Sell Date: {getDatetime()} \n Strategy: {strategy} \n Asset Type: {asset_type} \n ROV: {rov}% \n Sold For: {sold_for} \n Trader: {self.user['Name']} \n"

            # ADD TO CLOSED POSITIONS
            try:

                self.closed_positions.insert_one(obj)

            except writeConcernError:

                self.logger.ERROR(
                    f"INITIAL FAIL OF INSERTING CLOSED POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - writeConcernError")

                self.closed_positions.insert_one(obj)

            except writeError:

                self.logger.ERROR(
                    f"INITIAL FAIL OF INSERTING CLOSED POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - writeError")

                self.closed_positions.insert_one(obj)

            except Exception:

                self.logger.ERROR()

            # REMOVE FROM OPEN POSITIONS
            is_removed = self.open_positions.delete_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            try:

                if int(is_removed.deleted_count) == 0:

                    self.logger.ERROR(
                        f"INITIAL FAIL OF DELETING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj}")

                    self.open_positions.delete_one(
                        {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            except Exception:

                self.logger.ERROR()

            self.logger.INFO(
                f"{order_type} ORDER For {symbol} - TRADER: {self.user['Name']}", True)

        # REMOVE FROM QUEUE
        self.queue.delete_one({"Trader": self.user["Name"], "Symbol": symbol,
                               "Strategy": strategy, "Account_ID": self.account_id})

        self.push.send(msg)

    # RUN TRADER
    @exception_handler
    def runTrader(self, trade_data):
        """ METHOD RUNS ON A FOR LOOP ITERATING OVER THE TRADE DATA AND MAKING DECISIONS ON WHAT NEEDS TO BUY OR SELL.

        Args:
            trade_data ([list]): CONSISTS OF TWO DICTS TOP LEVEL, AND THEIR VALUES AS LISTS CONTAINING ALL THE TRADE DATA FOR EACH STOCK.
        """

        # UPDATE ALL ORDER STATUS'S
        self.updateStatus()

        # UPDATE USER ATTRIBUTE
        self.user = self.mongo.users.find_one({"Name": self.user["Name"]})

        for row in trade_data:

            strategy = row["Strategy"]

            symbol = row["Symbol"]

            asset_type = row["Asset_Type"]

            side = row["Side"]

            # CHECK OPEN POSITIONS AND QUEUE
            open_position = self.open_positions.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

            queued = self.queue.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

            strategy_object = self.strategies.find_one(
                {"Strategy": strategy, "Trader": self.user["Name"]})

            if not strategy_object:

                self.addNewStrategy(strategy, asset_type)

                strategy_object = self.strategies.find_one(
                    {"Trader": self.user["Name"], "Strategy": strategy})

            position_type = strategy_object["Position_Type"]

            row["Position_Type"] = position_type

            if not queued:

                direction = None

                # IS THERE AN OPEN POSITION ALREADY IN MONGO FOR THIS SYMBOL/STRATEGY COMBO
                if open_position:

                    direction = "CLOSE POSITION"

                    # NEED TO COVER SHORT
                    if side == "BUY" and position_type == "SHORT":

                        pass

                    # NEED TO SELL LONG
                    elif side == "SELL" and position_type == "LONG":

                        pass

                    # NEED TO SELL LONG OPTION
                    elif side == "SELL_TO_CLOSE" and position_type == "LONG":

                        pass

                    # NEED TO COVER SHORT OPTION
                    elif side == "BUY_TO_CLOSE" and position_type == "SHORT":

                        pass

                    else:

                        continue

                else:

                    direction = "OPEN POSITION"

                    # NEED TO GO LONG
                    if side == "BUY" and position_type == "LONG":

                        pass

                    # NEED TO GO SHORT
                    elif side == "SELL" and position_type == "SHORT":

                        pass

                    # NEED TO GO SHORT OPTION
                    elif side == "SELL_TO_OPEN" and position_type == "SHORT":

                        pass

                    # NEED TO GO LONG OPTION
                    elif side == "BUY_TO_OPEN" and position_type == "LONG":

                        pass

                    else:

                        continue

                if direction != None:

                    self.sendOrder(row if not open_position else row.update(
                        open_position), strategy_object, direction)
