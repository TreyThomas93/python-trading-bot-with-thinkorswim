
# imports
import time
from assets.exception_handler import exception_handler
from assets.helper_functions import getDatetime, selectSleep, modifiedAccountID


class Tasks:

    # THE TASKS CLASS IS USED FOR HANDLING ADDITIONAL TASKS OUTSIDE OF THE LIVE TRADER.
    # YOU CAN ADD METHODS THAT STORE PROFIT LOSS DATA TO MONGO, SELL OUT POSITIONS AT END OF DAY, ECT.
    # YOU CAN CREATE WHATEVER TASKS YOU WANT FOR THE BOT.
    # YOU CAN USE THE DISCORD CHANNEL NAMED TASKS IF YOU ANY HELP.

    def __init__(self):

        self.isAlive = True

    @exception_handler
    def checkOCOtriggers(self):
        """ Checks OCO triggers (stop loss/ take profit) to see if either one has filled. If so, then close position in mongo like normal.

        """

        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Order_Type": "OCO"})

        for position in open_positions:

            childOrderStrategies = position["childOrderStrategies"]

            for order_id in childOrderStrategies.keys():

                spec_order = self.tdameritrade.getSpecificOrder(order_id)

                new_status = spec_order["status"]

                if new_status == "FILLED":

                    self.pushOrder(position, spec_order)

                elif new_status == "CANCELED" or new_status == "REJECTED":

                    other = {
                        "Symbol": position["Symbol"],
                        "Order_Type": position["Order_Type"],
                        "Order_Status": new_status,
                        "Strategy": position["Strategy"],
                        "Trader": self.user["Name"],
                        "Date": getDatetime(),
                        "Account_ID": self.account_id
                    }

                    self.rejected.insert_one(
                        other) if new_status == "REJECTED" else self.canceled.insert_one(other)

                    self.logger.info(
                        f"{new_status.upper()} ORDER For {position['Symbol']} - TRADER: {self.user['Name']} - ACCOUNT ID: {modifiedAccountID(self.account_id)}")

                else:

                    self.open_positions.update_one({"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"]}, {
                        "$set": {f"childOrderStrategies.{order_id}.Order_Status": new_status}})

    @exception_handler
    def extractOCOchildren(self, spec_order):
        """This method extracts oco children order ids and then sends it to be stored in mongo open positions. 
        Data will be used by checkOCOtriggers with order ids to see if stop loss or take profit has been triggered.

        """

        oco_children = {
            "childOrderStrategies": {}
        }

        childOrderStrategies = spec_order["childOrderStrategies"][0]["childOrderStrategies"]

        for child in childOrderStrategies:

            oco_children["childOrderStrategies"][child["orderId"]] = {
                "Side": child["orderLegCollection"][0]["instruction"],
                "Exit_Price": child["stopPrice"] if "stopPrice" in child else child["price"],
                "Exit_Type": "STOP LOSS" if "stopPrice" in child else "TAKE PROFIT",
                "Order_Status": child["status"]
            }

        return oco_children

    @ exception_handler
    def addNewStrategy(self, strategy, asset_type):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        obj = {"Active": True,
               "Order_Type": "STANDARD",
               "Asset_Type": asset_type,
               "Position_Size": 500,
               "Position_Type": "LONG",
               "Trader": self.user["Name"],
               "Strategy": strategy,
               }

        # IF STRATEGY NOT IN STRATEGIES COLLECTION IN MONGO, THEN ADD IT

        self.strategies.update(
            {"Strategy": strategy},
            {"$setOnInsert": obj},
            upsert=True
        )

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.info(
            f"STARTING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})", extra={'log': False})

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                self.checkOCOtriggers()

                ##############################################################

            except KeyError:

                self.isAlive = False

            except Exception as e:

                self.logger.error(
                    f"ACCOUNT ID: {modifiedAccountID(self.account_id)} - TRADER: {self.user['Name']} - {e}")

            finally:

                time.sleep(selectSleep())

        self.logger.warning(
            f"TASK STOPPED FOR ACCOUNT ID {modifiedAccountID(self.account_id)}")
