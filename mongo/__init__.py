from pathlib import Path
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
ca = certifi.where()

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/config.env")

MONGO_URI = os.getenv('MONGO_URI')


class MongoDB:

    def __init__(self, logger):

        self.logger = logger

    def connect(self):

        try:

            self.logger.info("CONNECTING TO MONGO...", extra={'log': False})

            if MONGO_URI != None:

                self.client = MongoClient(
                    MONGO_URI, authSource="admin", tlsCAFile=ca)

                # SIMPLE TEST OF CONNECTION BEFORE CONTINUING
                self.client.server_info()

                self.db = self.client["Live_Trader"]

                self.users = self.db["users"]

                self.open_positions = self.db["open_positions"]

                self.closed_positions = self.db["closed_positions"]

                self.strategies = self.db["strategies"]

                self.rejected = self.db["rejected"]

                self.canceled = self.db["canceled"]

                self.queue = self.db["queue"]

                self.logger.info("CONNECTED TO MONGO!\n", extra={'log': False})

                return True

            else:

                raise Exception("MISSING MONGO URI")

        except Exception as e:

            self.logger.error(f"FAILED TO CONNECT TO MONGO! - {e}")

            return False
