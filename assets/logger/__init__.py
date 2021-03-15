# LOGGER CLASS WILL HANDLE ALL SYSTEM ALERTS. (INFO, WARNING, ERROR)
# imports
from datetime import datetime
import pytz
import os
import traceback
import colorama
from termcolor import colored

colorama.init()

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Logger:

    def __init__(self):

        self.gmail = None

        self.mongo = None

        self.push = None

    def getDatetime(self):

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        return datetime.strptime(dt_central.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

    def log(self, log, db=False, file_type="info"):
        """ METHOD LOGS TO FILE. IF DB EQUALS TRUE, THEN SAVE TO MONGO

        Args:
            log ([str]): LOG TO BE SAVED TO FILE/DB
            db (bool, optional): IF TRUE, THEN SAVE TO MONGO. Defaults to False.
        """

        try:

            with open(f"{THIS_FOLDER}/logs/{file_type}_{str(self.getDatetime()).split(' ')[0].replace('-', '_')}.txt", "a") as f:

                f.write(f"{log}\n")

        except Exception as e:

            print(e)

        if self.mongo != None and db:

            self.mongo.logs.insert_one({
                "Log": log,
                "Date": self.getDatetime()
            })

    def INFO(self, info, db=False):
        """ METHOD PRINTS OUT INFO TO CONSOLE

        Args:
            info ([str]): MESSAGE
            db (bool, optional): IF TRUE, THEN SAVE TO MONGO. Defaults to False.
        """

        # LEVEL:DATETIME:INFO
        log = f"INFO | {self.getDatetime()} | {info}"

        print(colored(log, "green"))

        self.log(log, db)

    def WARNING(self, filename, warning):
        """ METHOD PRINTS OUT WARNING TO CONSOLE.

        Args:
            filename ([str]): NAME OF FILE WHERE WARNING OCCURED
            warning ([str]): MESSAGE
        """

        # LEVEL:DATETIME:FILENAME:WARNING
        log = f"WARNING | {self.getDatetime()} | {filename} | {warning}"

        print(colored(log, "orange"))

        self.log(log)

    def ERROR(self, error=None):
        """ METHOD PRINTS OUT ERROR WITH TRACEBACK TO CONSOLE

        Args:
            error ([str], optional): ERROR MESSAGE IF THERE IS ONE. Defaults to None.
        """

        # LEVEL:DATETIME
        if error == None:

            log = f"ERROR | {self.getDatetime()}"

        # LEVEL:DATETIME:ERROR
        else:

            log = f"ERROR | {self.getDatetime()} | {error}"

        print(colored(log, "red"))

        tb = traceback.format_exc()

        print(tb)

        log = f"{log}\n{tb}"

        self.log(log, file_type="error")

        # self.push.send(log)

    def CRITICAL(self, error):
        """ METHOD PRINTS OUT CRITICAL TO CONSOLE.

        Args:
            error ([str]): ERROR MESSAGE
        """

        # LEVEL:DATETIME:MESSAGE
        log = f"CRITICAL | {self.getDatetime()} | {error}"

        print(colored(log, "red"))

        self.log(log, file_type="error")
