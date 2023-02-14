

from logging import Logger
import os
from random import randint
from src.models.order_model import Order
from src.trader import Trader
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

THIS_FOLDER = os.path.dirname(os.path.abspath(
    __file__)).replace("services", "utils")

sides = ["BUY", "SELL"]

strategies = ['REVA', 'RSI_Swing', 'SMA_EMA']

_symbols = ['ABC', 'DEF', 'GHI']


class Gmail:

    def __init__(self, logger) -> None:
        self.logger: Logger = logger
        self.SCOPES: list = ["https://mail.google.com/"]
        self.credentials: Credentials = None
        self.service = None
        self.tokenFile: str = f"{THIS_FOLDER}/credentials/token.json"
        self.credentialsFile: str = f"{THIS_FOLDER}/credentials/credentials.json"

    def connect(self) -> bool:
        try:
            self.logger.info("Connecting to gmail...", extra={'log': False})

            if not os.path.exists(self.credentialsFile):
                raise Exception("credentials.json file not found.")

            if os.path.exists(self.tokenFile):
                self.credentials = Credentials.from_authorized_user_file(
                    self.tokenFile, self.SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentialsFile, self.SCOPES)
                self.credentials = flow.run_local_server(port=0)

            if self.credentials != None:

                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())

                # Save the credentials for the next run
                with open(self.tokenFile, 'w') as token:
                    token.write(self.credentials.to_json())

                self.service = build(
                    'gmail', 'v1', credentials=self.credentials)
                self.logger.info("Connected to gmail.\n", extra={'log': False})

                return True

            else:
                raise Exception("Gmail credentials not found.")

        except Exception as e:
            self.logger.error(f"Error connecting to Gmail: {e}")
            return False

    def getEmails(self) -> list:
        # extractedEmailData = [
        #     f"Alert: New Symbol: {_symbols[randint(0, len(_symbols) - 1)]} was added to {strategies[randint(0, len(strategies) - 1)]}, {sides[randint(0, len(sides) - 1)]}"]

        # GETS LIST OF ALL EMAILS
        results = self.service.users().messages().list(userId='me').execute()

        payloads: list = []

        if results['resultSizeEstimate'] != 0:
            # {'id': '173da9a232284f0f', 'threadId': '173da9a232284f0f'}
            for index, message in enumerate(results["messages"]):
                try:
                    result = self.service.users().messages().get(
                        id=message["id"], userId="me", format="metadata").execute()

                    for payload in result['payload']["headers"]:
                        if payload["name"] == "Subject":
                            payloads.append(payload["value"].strip())
                except:
                    pass
                finally:
                    # MOVE EMAIL TO TRASH FOLDER
                    self.service.users().messages().trash(
                        userId='me', id=message["id"]).execute()

                    print(
                        f'Moved email to trash. {index + 1}/{len(results["messages"])}')

        tradeData: list = []

        for data in payloads:
            try:
                seperate = data.split(":")

                if len(seperate) > 1:
                    contains = ["were added to", "was added to"]

                    for i in contains:
                        if i in seperate[2]:
                            sep = seperate[2].split(i)
                            symbols = sep[0].strip().split(",")
                            strategy, side = sep[1].strip().split(",")

                            for symbol in symbols:
                                if strategy != "" and side != "":
                                    tradeData.append({'symbol': symbol.strip(), 'side': side.replace(".", " ").upper().strip(), 'strategy': strategy.replace(
                                        ".", " ").upper().strip()
                                    })
            except Exception as e:
                self.logger.error(f"Error parsing email: {e}")

        return tradeData
