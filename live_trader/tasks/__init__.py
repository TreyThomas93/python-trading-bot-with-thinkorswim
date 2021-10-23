
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

    @ exception_handler
    def addNewStrategy(self, strategy, asset_type):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        obj = {"Active": True,
               "Order_Type": "Standard",
               "Asset_Type": asset_type,
               "Position_Size": 500,
               "Position_Type": "Long",
               "Trader": self.user["Name"],
               "Strategy": strategy,
               }

        # IF STRATEGY NOT IN STRATEGIES COLLECTION IN MONGO, THEN ADD IT
        # self.strategies.update({"Name": self.user["Name"], strategy: {"$exists": False}}, {
        #     "$set": {f"Accounts.{self.account_id}.Strategies.{strategy}": obj}})

        resp = self.strategies.update(
            {"Strategy": strategy},
            {"$setOnInsert": obj},
            upsert=True
        )

        print(resp)

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.INFO(
            f"STARTING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})\n")

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                pass

                ##############################################################
            except KeyError:

                self.isAlive = False

            except Exception:

                self.logger.ERROR(
                    f"ACCOUNT ID: {modifiedAccountID(self.account_id)} - TRADER: {self.user['Name']}")

            finally:

                time.sleep(selectSleep())

        self.logger.INFO(
            f"TASK STOPPED FOR ACCOUNT ID {modifiedAccountID(self.account_id)}")
