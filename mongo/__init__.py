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
RUN_LIVE_TRADER = True if os.getenv('RUN_LIVE_TRADER') == "True" else False


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

                self.users = self.client["Live_Trader"]["users"]

                self.strategies = self.client["Live_Trader"]["strategies"]

                self.db = self.client["Live_Trader" if RUN_LIVE_TRADER else "Paper_Trader"]

                self.open_positions = self.db["open_positions"]

                self.closed_positions = self.db["closed_positions"]

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
