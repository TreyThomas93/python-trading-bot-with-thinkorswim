from assets.helper_functions import getDatetime, modifiedAccountID
from api_trader.tasks import Tasks
from threading import Thread
from assets.exception_handler import exception_handler
from api_trader.order_builder import OrderBuilder
from dotenv import load_dotenv
from pathlib import Path
import os
from pymongo.errors import WriteError, WriteConcernError
import traceback
import time
from random import randint


THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

RUN_TASKS = True if os.getenv('RUN_TASKS') == "True" else False


class ApiTrader(Tasks, OrderBuilder):

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

        self.RUN_LIVE_TRADER = True if user["Accounts"][str(
            account_id)]["Account_Position"] == "Live" else False

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

        # If user wants to run tasks
        if RUN_TASKS:

            Thread(target=self.runTasks, daemon=True).start()

        else:

            self.logger.info(
                f"NOT RUNNING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})\n", extra={'log': False})

        self.logger.info(
            f"RUNNING {user['Accounts'][str(account_id)]['Account_Position'].upper()} TRADER ({modifiedAccountID(self.account_id)})\n")

    # STEP ONE
    @exception_handler
    def sendOrder(self, trade_data, strategy_object, direction):

        symbol = trade_data["Symbol"]

        strategy = trade_data["Strategy"]

        side = trade_data["Side"]

        order_type = strategy_object["Order_Type"]

        if order_type == "STANDARD":

            order, obj = self.standardOrder(
                trade_data, strategy_object, direction)

        elif order_type == "OCO":

            order, obj = self.OCOorder(trade_data, strategy_object, direction)

        if order == None and obj == None:

            return

        # PLACE ORDER IF LIVE TRADER ################################################
        if self.RUN_LIVE_TRADER:

            resp = self.tdameritrade.placeTDAOrder(order)

            status_code = resp.status_code

            if status_code not in [200, 201]:

                other = {
                    "Symbol": symbol,
                    "Order_Type": side,
                    "Order_Status": "REJECTED",
                    "Strategy": strategy,
                    "Trader": self.user["Name"],
                    "Date": getDatetime(),
                    "Account_ID": self.account_id
                }

                self.logger.info(
                    f"{symbol} Rejected For {self.user['Name']} ({modifiedAccountID(self.account_id)}) - Reason: {(resp.json())['error']} ")

                self.rejected.insert_one(other)

                return

            # GETS ORDER ID FROM RESPONSE HEADERS LOCATION
            obj["Order_ID"] = int(
                (resp.headers["Location"]).split("/")[-1].strip())

            obj["Account_Position"] = "Live"

        else:

            obj["Order_ID"] = -1*randint(100_000_000, 999_999_999)

            obj["Account_Position"] = "Paper"

        obj["Order_Status"] = "QUEUED"

        self.queueOrder(obj)

        response_msg = f"{'Live Trade' if self.RUN_LIVE_TRADER else 'Paper Trade'}: {side} Order for Symbol {symbol} ({modifiedAccountID(self.account_id)})"

        self.logger.info(response_msg)

    # STEP TWO
    @exception_handler
    def queueOrder(self, order):
        """ METHOD FOR QUEUEING ORDER TO QUEUE COLLECTION IN MONGODB

        Args:
            order ([dict]): [ORDER DATA TO BE PLACED IN QUEUE COLLECTION]
        """
        # ADD TO QUEUE WITHOUT ORDER ID AND STATUS
        self.queue.update_one(
            {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]}, {"$set": order}, upsert=True)

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

            # ORDER ID NOT FOUND. ASSUME REMOVED OR PAPER TRADING
            if "error" in spec_order:

                custom = {
                    "price": queue_order["Entry_Price"] if queue_order["Direction"] == "OPEN POSITION" else queue_order["Exit_Price"],
                    "shares": queue_order["Qty"]
                }

                # IF RUNNING LIVE TRADER, THEN ASSUME DATA
                if self.RUN_LIVE_TRADER:

                    data_integrity = "Assumed"

                    self.logger.warning(
                        f"Order ID Not Found. Moving {queue_order['Symbol']} {queue_order['Order_Type']} Order To {queue_order['Direction']} Positions ({modifiedAccountID(self.account_id)})")

                else:

                    data_integrity = "Reliable"

                    self.logger.info(
                        f"Paper Trader - Sending Queue Order To PushOrder ({modifiedAccountID(self.account_id)})")

                self.pushOrder(queue_order, custom, data_integrity)

                continue

            new_status = spec_order["status"]

            order_type = queue_order["Order_Type"]

            # CHECK IF QUEUE ORDER ID EQUALS TDA ORDER ID
            if queue_order["Order_ID"] == spec_order["orderId"]:

                if new_status == "FILLED":

                    # CHECK IF OCO ORDER AND THEN GET THE CHILDREN
                    if queue_order["Order_Type"] == "OCO":

                        queue_order = {**queue_order, **
                                       self.extractOCOchildren(spec_order)}

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

                    self.logger.info(
                        f"{new_status.upper()} Order For {queue_order['Symbol']} ({modifiedAccountID(self.account_id)})")

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

        price = round(price, 2) if price >= 1 else round(price, 4)

        strategy = queue_order["Strategy"]

        side = queue_order["Side"]

        account_id = queue_order["Account_ID"]

        position_size = queue_order["Position_Size"]

        asset_type = queue_order["Asset_Type"]

        position_type = queue_order["Position_Type"]

        direction = queue_order["Direction"]

        account_position = queue_order["Account_Position"]

        order_type = queue_order["Order_Type"]

        obj = {
            "Symbol": symbol,
            "Strategy": strategy,
            "Position_Size": position_size,
            "Position_Type": position_type,
            "Data_Integrity": data_integrity,
            "Trader": self.user["Name"],
            "Account_ID": account_id,
            "Asset_Type": asset_type,
            "Account_Position": account_position,
            "Order_Type": order_type
        }

        if asset_type == "OPTION":

            obj["Pre_Symbol"] = queue_order["Pre_Symbol"]

            obj["Exp_Date"] = queue_order["Exp_Date"]

            obj["Option_Type"] = queue_order["Option_Type"]

        collection_insert = None

        message_to_push = None

        if direction == "OPEN POSITION":

            obj["Qty"] = shares

            obj["Entry_Price"] = price

            obj["Entry_Date"] = getDatetime()

            collection_insert = self.open_positions.insert_one

            message_to_push = f">>>> \n Side: {side} \n Symbol: {symbol} \n Qty: {shares} \n Price: ${price} \n Strategy: {strategy} \n Asset Type: {asset_type} \n Date: {getDatetime()} \n Trader: {self.user['Name']} \n Account Position: {'Live Trade' if self.RUN_LIVE_TRADER else 'Paper Trade'}"

        elif direction == "CLOSE POSITION":

            position = self.open_positions.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            obj["Qty"] = position["Qty"]

            obj["Entry_Price"] = position["Entry_Price"]

            obj["Entry_Date"] = position["Entry_Date"]

            obj["Exit_Price"] = price

            obj["Exit_Date"] = getDatetime()

            exit_price = round(price * position["Qty"], 2)

            entry_price = round(
                position["Entry_Price"] * position["Qty"], 2)

            collection_insert = self.closed_positions.insert_one

            message_to_push = f"____ \n Side: {side} \n Symbol: {symbol} \n Qty: {position['Qty']} \n Entry Price: ${position['Entry_Price']} \n Entry Date: {position['Entry_Date']} \n Exit Price: ${price} \n Exit Date: {getDatetime()} \n Strategy: {strategy} \n Asset Type: {asset_type} \n Trader: {self.user['Name']} \n Account Position: {'Live Trade' if self.RUN_LIVE_TRADER else 'Paper Trade'}"

            # REMOVE FROM OPEN POSITIONS
            is_removed = self.open_positions.delete_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            try:

                if int(is_removed.deleted_count) == 0:

                    self.logger.error(
                        f"INITIAL FAIL OF DELETING OPEN POSITION FOR SYMBOL {symbol} - {self.user['Name']} ({modifiedAccountID(self.account_id)})")

                    self.open_positions.delete_one(
                        {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            except Exception:

                msg = f"{self.user['Name']} - {modifiedAccountID(self.account_id)} - {traceback.format_exc()}"

                self.logger.error(msg)

        # PUSH OBJECT TO MONGO. IF WRITE ERROR THEN ONE RETRY WILL OCCUR. IF YOU SEE THIS ERROR, THEN YOU MUST CONFIRM THE PUSH OCCURED.
        try:

            collection_insert(obj)

        except WriteConcernError as e:

            self.logger.error(
                f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - {e}")

            collection_insert(obj)

        except WriteError as e:

            self.logger.error(
                f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - {e}")

            collection_insert(obj)

        except Exception:

            msg = f"{self.user['Name']} - {modifiedAccountID(self.account_id)} - {traceback.format_exc()}"

            self.logger.error(msg)

        self.logger.info(
            f"Pushing {side} Order For {symbol} To {'Open Positions' if direction == 'OPEN POSITION' else 'Closed Positions'} ({modifiedAccountID(self.account_id)})")

        # REMOVE FROM QUEUE
        self.queue.delete_one({"Trader": self.user["Name"], "Symbol": symbol,
                               "Strategy": strategy, "Account_ID": self.account_id})

        self.push.send(message_to_push)

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

        # FORBIDDEN SYMBOLS
        forbidden_symbols = self.mongo.forbidden.find({"Account_ID": str(self.account_id)})

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
                {"Strategy": strategy, "Account_ID": self.account_id})

            if not strategy_object:

                self.addNewStrategy(strategy, asset_type)

                strategy_object = self.strategies.find_one(
                    {"Account_ID": self.account_id, "Strategy": strategy})

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

                elif not open_position and symbol not in forbidden_symbols:

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

                    self.sendOrder(row if not open_position else {
                                   **row, **open_position}, strategy_object, direction)
