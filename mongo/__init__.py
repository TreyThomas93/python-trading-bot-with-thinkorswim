import colorama
from termcolor import colored
from pymongo import MongoClient
from dotenv import load_dotenv
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

load_dotenv(dotenv_path=f"{THIS_FOLDER}/.env")

colorama.init()

MONGO_URI = os.getenv('MONGO_URI')


class MongoDB:

    def __init__(self, logger):

        try:

            logger.INFO("CONNECTING TO MONGO...")

            if MONGO_URI != None:

                self.client = MongoClient(MONGO_URI, authSource="admin")

                self.db = self.client["Live_Trader"]

                self.users = self.db["users"]

                self.open_positions = self.db["open_positions"]

                self.closed_positions = self.db["closed_positions"]

                self.strategy_history = self.db["strategy_history"]

                self.other = self.db["other"]

                self.queue = self.db["queue"]

                self.logs = self.db["logs"]

                self.emails = self.db["emails"]

                self.system = self.db["system"]

                self.balance_history = self.db["balance_history"]

                self.open_positions_history = self.db["open_positions_history"]

                self.closed_positions_history = self.db["closed_positions_history"]

                logger.INFO("CONNECTED TO MONGO!\n")

            else:

                raise Exception("MONGO URI IS NONETYPE")

        except Exception:

            logger.CRITICAL("FAILED TO CONNECT TO MONGO!")
