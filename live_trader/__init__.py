from assets.current_datetime import getDatetime
from tasks import Tasks
from threading import Thread
from assets.exception_handler import exception_handler
from pprint import pprint


class LiveTrader(Tasks):

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

        self.other = mongo.other

        self.queue = mongo.queue

        self.logger = logger

        self.no_ids_list = []

        Tasks.__init__(self)

        Thread(target=self.runTasks, daemon=True).start()

    # STEP ONE
    @exception_handler
    def placeOrder(self, trade_data, position_data=None):
        """ METHOD IS USED TO PLACE TRADES (BUY/SELL ORDER).

        Args:
            trade_data ([dict]): [CONSISTS OF TRADE DATA FOR EACH SYMBOL (SYMBOL, STRATEGY, AGGREGATION, ASSET TYPE, ACCOUNT ID, ORDER TYPE)]
            position_data ([dict], optional): [CONSISTS OF OPEN POSITION DATA IF SELL ORDER]. Defaults to None.
            orderType (str, optional): [EITHER A LIMIT ORDER OR MARKET ORDER]. Defaults to "LIMIT".
        """
        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        if "Pre_Symbol" in trade_data:

            asset_type = "OPTION"

        else:

            asset_type = "EQUITY"

        order = {
            "orderType": "LIMIT",
            "price": None,
            "session": "SEAMLESS" if asset_type == "EQUITY" else "NORMAL",
            "duration": "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": side,
                    "quantity": None,
                    "instrument": {
                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"],
                        "assetType": asset_type,
                    }
                }
            ]
        }

        obj = {
            "Symbol": symbol,
            "Qty": None,
            "Position_Size": None,
            "Date": getDatetime(),
            "Strategy": strategy,
            "Trader": self.user["Name"],
            "Order_ID": None,
            "Order_Status": None,
            "Order_Type": side,
            "Asset_Type": asset_type,
            "Account_ID": self.account_id,
        }

        if asset_type == "OPTION":

            obj["Pre_Symbol"] = trade_data["Pre_Symbol"]

            obj["Exp_Date"] = trade_data["Exp_Date"]

            obj["Option_Type"] = trade_data["Option_Type"]

            order["orderLegCollection"][0]["instrument"]["putCall"] = trade_data["Option_Type"]

        position_size = None

        if side == "BUY" or side == "BUY_TO_OPEN":

            resp = self.tdameritrade.getQuote(symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])
            
            price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]]["bidPrice"])
            
            order["price"] = round(price, 2) if price >= 1 else round(price, 4)

            # GET SHARES FOR PARTICULAR STRATEGY
            strategies = self.user["Accounts"][str(
                self.account_id)]["Strategies"]

            if strategy not in strategies:

                self.updateStrategiesObject(strategy)

                strategies = self.mongo.users.find_one({"Name": self.user["Name"]})["Accounts"][str(
                self.account_id)]["Strategies"]

            position_size = int(strategies[strategy]["Position_Size"])

            active_strategy = strategies[strategy]["Active"]

            shares = int(position_size/price)

            if active_strategy and shares > 0:

                order["orderLegCollection"][0]["quantity"] = shares

                obj["Qty"] = shares

                obj["Position_Size"] = position_size

                obj["Buy_Price"] = price

            else:

                return

        elif side == "SELL" or side == "SELL_TO_CLOSE":

            resp = self.tdameritrade.getQuote(symbol)

            price = float(resp[symbol]["askPrice"])

            order["price"] = round(price, 2) if price >= 1 else round(price, 4)

            order["orderLegCollection"][0]["quantity"] = position_data["Qty"]

            obj["Buy_Price"] = position_data["Buy_Price"]

            obj["Buy_Date"] = position_data["Date"]

            obj["Qty"] = position_data["Qty"]

            obj["Position_Size"] = position_data["Position_Size"]

            position_size = position_data["Position_Size"]
        # PLACE ORDER ################################################
        
        resp = self.tdameritrade.placeTDAOrder(order)

        status_code = resp.status_code

        acceptable_status = [200, 201]

        if status_code not in acceptable_status:

            other = {
                "Symbol": symbol,
                "Position_Size": position_size,
                "Order_Type": side,
                "Order_Status": "REJECTED",
                "Strategy": strategy,
                "Trader": self.user["Name"],
                "Date": getDatetime(),
                "Account_ID": self.account_id
            }

            self.logger.INFO(
                f"{symbol} REJECTED For {self.user['Name']} - REASON: {(resp.json())['error']}", True)

            self.other.insert_one(other)

            return

        # GETS ORDER ID FROM RESPONSE HEADERS LOCATION
        obj["Order_ID"] = int(
            (resp.headers["Location"]).split("/")[-1].strip())

        obj["Order_Status"] = "QUEUED"

        self.queueOrder(obj)

        response_msg = f"{side} ORDER RESPONSE: {resp.status_code} - SYMBOL: {symbol} - TRADER: {self.user['Name']} - ACCOUNT ID: {self.account_id}"

        self.logger.INFO(response_msg)

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
        """

        queued_orders = self.queue.find({"Trader": self.user["Name"], "Order_ID": {
                                        "$ne": None}, "Account_ID": self.account_id})

        for queue_order in queued_orders:

            spec_order = self.tdameritrade.getSpecificOrder(
                queue_order["Order_ID"])

            if "error" in spec_order:

                direction = "OPEN" if queue_order["Order_Type"] == "BUY" else "CLOSED"

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

                    self.other.insert_one(other)

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

        # MAY SET THESE DYNAMICALLY FROM WEB APP
        forbidden_symbols = self.user["Accounts"][str(
            self.account_id)]["forbidden_symbols"]

        for data in trade_data:

            side = data["Side"]

            strategy = data["Strategy"]

            symbol = data["Symbol"]

            account_id = data["Account_ID"]

            # IF SYMBOL NOT FORBIDDEN AND ACCOUNT TYPE (PRIMARY, SECONDARY) IS EQUAL TO THE ACCOUNT TYPE ASSOCIATED WITH THE TDAMERITRADE ACCOUNT TYPE
            if symbol not in forbidden_symbols and self.account_id == account_id:

                # CHECK OPEN POSITIONS AND QUEUE
                open_position = self.open_positions.find_one(
                    {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

                queued = self.queue.find_one(
                    {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

                # BUY ##############################
                if side == "BUY" or side == "BUY_TO_OPEN":

                    if not open_position and not queued:

                        # LIVE TRADE
                        # THIS CHECK IF USER IS ACTIVE. IF NOT ACTIVE, ALL BUYING STOPS
                        if self.user["Accounts"][str(self.account_id)]["Active"]:

                            self.placeOrder(data)

                    elif open_position:

                        self.logger.INFO(
                            f"Symbol {symbol} with strategy {strategy} already an open position")

                    elif queued:

                        self.logger.INFO(
                            f"Symbol {symbol} with strategy {strategy} already in queue")

                # SELL ##############################
                elif side == "SELL" or side == "SELL_TO_CLOSE":

                    if open_position and not queued:

                        # LIVE TRADE
                        self.placeOrder(data, open_position)

# {'accountId': 123456789,
#  'cancelTime': '2021-04-19',
#  'cancelable': False,
#  'closeTime': '2020-10-21T18:01:04+0000',
#  'complexOrderStrategyType': 'NONE',
#  'destinationLinkName': 'NITE',
#  'duration': 'GOOD_TILL_CANCEL',
#  'editable': False,
#  'enteredTime': '2020-10-21T18:01:04+0000',
#  'filledQuantity': 1.0,
#  'orderActivityCollection': [{'activityType': 'EXECUTION',
#                               'executionLegs': [{'legId': 1,
#                                                  'mismarkedQuantity': 0.0,
#                                                  'price': 25.62,
#                                                  'quantity': 1.0,
#                                                  'time': '2020-10-21T18:01:04+0000'}],
#                               'executionType': 'FILL',
#                               'orderRemainingQuantity': 0.0,
#                               'quantity': 1.0}],
#  'orderId': 1598640932,
#  'orderLegCollection': [{'instruction': 'SELL',
#                          'instrument': {'assetType': 'EQUITY',
#                                         'cusip': 'G0750C108',
#                                         'symbol': 'AXTA'},
#                          'legId': 1,
#                          'orderLegType': 'EQUITY',
#                          'positionEffect': 'CLOSING',
#                          'quantity': 1.0}],
#  'orderStrategyType': 'SINGLE',
#  'orderType': 'LIMIT',
#  'price': 25.49,
#  'quantity': 1.0,
#  'remainingQuantity': 0.0,
#  'requestedDestination': 'AUTO',
#  'session': 'SEAMLESS',
#  'status': 'FILLED',
#  'tag': 'AA_JohnDoe'}
