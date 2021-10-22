from pprint import pprint
from dotenv import load_dotenv
import requests
import os
from pathlib import Path

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)

load_dotenv(dotenv_path=f"{path.parent}/.env")

PUSH_API_KEY = os.getenv('PUSH_API_KEY')


class PushNotification:

    def __init__(self, device_id, logger, gmail):

        self.url = 'https://www.pushsafer.com/api'

        self.post_fields = {
            "t": "TOS Trading Bot",
            "m": None,
            "s": 0,
            "v": 1,
            "i": 1,
            "c": "#E94B3C",
            "d": device_id,
            "ut": "TOS Trading Bot",
            "k": PUSH_API_KEY,
        }

        self.logger = logger

        self.gmail = gmail

        self.remaining_alert_sent = False

    def send(self, notification):
        """ METHOD SENDS PUSH NOTIFICATION TO USER

        Args: 
            notification ([str]): MESSAGE TO BE SENT
        """

        try:

            # RESPONSE: {'status': 1, 'success': 'message transmitted', 'available': 983, 'message_ids': '18265430:34011'}

            self.post_fields["m"] = notification

            response = requests.post(self.url, self.post_fields)

            if response.json()["success"] == 'message transmitted':

                self.logger.INFO(f"PUSH NOTIFICATION SUCCESS: {notification}")

            else:

                self.logger.INFO(f"PUSH NOTIFICATION FAILED: {notification}")

        except ValueError:

            pass

        except KeyError:

            pass

        except Exception:

            self.logger.ERROR()
