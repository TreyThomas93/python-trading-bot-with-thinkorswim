# LOGGER CLASS WILL HANDLE ALL SYSTEM ALERTS. (INFO, WARNING, ERROR)
# imports
import os
import traceback
import colorama
from termcolor import colored
from assets.helper_functions import getDatetime

colorama.init()

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Logger:

    def __init__(self):

        self.push = None

    def log(self, log, file_type="info"):
        """ METHOD LOGS TO FILE. IF DB EQUALS TRUE, THEN SAVE TO MONGO

        Args:
            log ([str]): LOG TO BE SAVED TO FILE/DB
            db (bool, optional): IF TRUE, THEN SAVE TO MONGO. Defaults to False.
        """

        try:

            with open(f"{THIS_FOLDER}/logs/{file_type}{(getDatetime().strftime('%Y-%m-%d')).split(' ')[0].replace('-', '_')}.txt", "a") as f:

                f.write(f"{log}\n")

        except Exception as e:

            print(e)

    def INFO(self, info):
        """ METHOD PRINTS OUT INFO TO CONSOLE

        Args:
            info ([str]): MESSAGE
            db (bool, optional): IF TRUE, THEN SAVE TO MONGO. Defaults to False.
        """

        # LEVEL:DATETIME:INFO
        log = f"INFO | {getDatetime()} | {info}"

        print(colored(log, "green"))

        self.log(log)

    def WARNING(self, filename, warning):
        """ METHOD PRINTS OUT WARNING TO CONSOLE.

        Args:
            filename ([str]): NAME OF FILE WHERE WARNING OCCURED
            warning ([str]): MESSAGE
        """

        # LEVEL:DATETIME:FILENAME:WARNING
        log = f"WARNING | {getDatetime()} | {filename} | {warning}"

        print(colored(log, "cyan"))

        self.log(log)

    def ERROR(self, error=None):
        """ METHOD PRINTS OUT ERROR WITH TRACEBACK TO CONSOLE

        Args:
            error ([str], optional): ERROR MESSAGE IF THERE IS ONE. Defaults to None.
        """

        # LEVEL:DATETIME
        if error == None:

            log = f"ERROR | {getDatetime()}"

        # LEVEL:DATETIME:ERROR
        else:

            log = f"ERROR | {getDatetime()} | {error}"

        print(colored(log, "red"))

        tb = traceback.format_exc()

        print(tb)

        log = f"{log}\n{tb}"

        self.log(log, file_type="error")

    def CRITICAL(self, error):
        """ METHOD PRINTS OUT CRITICAL TO CONSOLE.

        Args:
            error ([str]): ERROR MESSAGE
        """

        # LEVEL:DATETIME:MESSAGE
        log = f"CRITICAL | {getDatetime()} | {error}"

        print(colored(log, "red"))

        self.log(log, file_type="error")
