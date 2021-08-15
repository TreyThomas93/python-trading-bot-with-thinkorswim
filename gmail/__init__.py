##################################################################################
# GMAIL CLASS ####################################################################
# Handles email auth and messages ################################################

# imports
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os.path
import os
from pprint import pprint

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Gmail():

    def __init__(self, logger):

        self.logger = logger

        self.SCOPES = ["https://mail.google.com/"]

        self.creds = None

        self.service = None

        self.token_file = f"{THIS_FOLDER}/creds/token.json"

        self.creds_file = f"{THIS_FOLDER}/creds/credentials.json"

    def connect(self):
        """ METHOD SETS ATTRIBUTES AND CONNECTS TO GMAIL API

        Args:
            mongo ([object]): MONGODB OBJECT
            logger ([object]): LOGGER OBJECT
        """

        try:

            self.logger.INFO("CONNECTING TO GMAIL...")

            if os.path.exists(self.token_file):

                with open(self.token_file, 'r') as token:

                    self.creds = Credentials.from_authorized_user_file(
                        self.token_file, self.SCOPES)

            if not self.creds:

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_file, self.SCOPES)

                self.creds = flow.run_local_server(port=0)

            elif self.creds and self.creds.expired and self.creds.refresh_token:

                self.creds.refresh(Request())

            if self.creds != None:
                
                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:

                    token.write(self.creds.to_json())

                self.service = build('gmail', 'v1', credentials=self.creds)

                self.logger.INFO("CONNECTED TO GMAIL!\n")

                return True

            else:

                raise Exception("Creds Not Found!")

        except Exception as e:
            print(e)
            self.logger.CRITICAL("FAILED TO CONNECT TO GMAIL!\n")

            return False

    def extractSymbolsFromEmails(self, payloads):
        """ METHOD TAKES SUBJECT LINES OF THE EMAILS WITH THE SYMBOLS AND SCANNER NAMES AND EXTRACTS THE NEEDED THE INFO FROM THEM.
            NEEDED INFO: Symbol, Strategy, Side(Buy/Sell), Account ID

        Args:
            payloads ([list]): LIST OF EMAIL CONTENT

        Returns:
            [dict]: LIST OF EXTRACTED EMAIL CONTENT
        """

        trade_data = []

        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY, ACCOUNT ID
        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY, ACCOUNT ID

        for payload in payloads:

            try:

                seperate = payload.split(":")

                if len(seperate) > 1:

                    contains = ["were added to", "was added to"]

                    for i in contains:

                        if i in seperate[2]:

                            sep = seperate[2].split(i)

                            symbols = sep[0].strip().split(",")

                            strategy, side, * \
                                account_ids = sep[1].strip().split(",")

                            account_ids = [int(account_id.replace(
                                ".", " ").strip()) for account_id in account_ids]

                            for symbol in symbols:

                                if strategy != "" and side != "" and len(account_ids) > 0:

                                    # ITERATE OVER LIST OF ACCOUNT IDS FOR THIS PARTICULAR STRATEGY AND SYMBOL
                                    for account_id in account_ids:

                                        obj = {
                                            "Symbol": symbol.strip(),
                                            "Side": side.upper().strip(),
                                            "Strategy": strategy.replace(".", " ").strip(),
                                            "Account_ID": account_id
                                        }

                                        trade_data.append(obj)

                                else:

                                    self.logger.ERROR(
                                        f"MISSING FIELDS FOR STRATEGY {strategy}")

                            break

                    self.logger.INFO(f"NEW EMAIL: {payload}")

            except IndexError:

                pass

            except ValueError:

                self.logger.ERROR(error=f"EMAIL FORMAT ERROR: {payload}")

            except Exception:

                self.logger.ERROR()

        return trade_data

    def getEmails(self):
        """ METHOD RETRIEVES EMAILS FROM INBOX, ADDS EMAIL TO TRASH FOLDER, AND ADD THEIR CONTENT TO payloads LIST TO BE EXTRACTED.

        Returns:
            [dict]: LIST RETURNED FROM extractSymbolsFromEmails METHOD
        """

        payloads = []

        try:

            # GETS LIST OF ALL EMAILS
            results = self.service.users().messages().list(userId='me').execute()

            if results['resultSizeEstimate'] != 0:

                # {'id': '173da9a232284f0f', 'threadId': '173da9a232284f0f'}
                for message in results["messages"]:

                    result = self.service.users().messages().get(
                        id=message["id"], userId="me", format="metadata").execute()

                    for payload in result['payload']["headers"]:

                        if payload["name"] == "Subject":

                            payloads.append(payload["value"].strip())

                    # MOVE EMAIL TO TRASH FOLDER
                    self.service.users().messages().trash(
                        userId='me', id=message["id"]).execute()

        except Exception:

            self.logger.ERROR()

        finally:

            return self.extractSymbolsFromEmails(payloads)
