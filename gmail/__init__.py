##################################################################################
# GMAIL CLASS ####################################################################
# Handles email auth and messages ################################################

# imports
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os.path
import pickle
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import json
from datetime import datetime
import pytz
import os

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Gmail():

    def __init__(self, mongo, logger):
        """ METHOD SETS ATTRIBUTES AND CONNECTS TO GMAIL API

        Args:
            mongo ([object]): MONGODB OBJECT
            logger ([object]): LOGGER OBJECT
        """

        self.SCOPES = ["https://mail.google.com/"]

        self.logger = logger

        self.creds = None

        self.service = None

        self.users = mongo.users

        self.emails = mongo.emails

        self.ids_to_delete = []

        self.token_file = f"{THIS_FOLDER}/creds/token.json"

        self.creds_file = f"{THIS_FOLDER}/creds/credentials.json"

        try:

            self.logger.INFO("CONNECTING TO GMAIL...")

            if os.path.exists(self.token_file):
                
                with open(self.token_file, 'r') as token:
                    
                    self.creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
                    
            # If there are no (valid) credentials available, let the user log in.
            if not self.creds or not self.creds.valid:

                if self.creds and self.creds.expired and self.creds.refresh_token:

                    self.creds.refresh(Request())

                else:

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.creds_file, self.SCOPES)

                    self.creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:

                    token.write(self.creds.to_json())

            self.service = build('gmail', 'v1', credentials=self.creds)

            self.logger.INFO("CONNECTED TO GMAIL!\n")

        except Exception as e:
            print(e)
            self.logger.CRITICAL("FAILED TO CONNECT TO GMAIL!\n")

    def deleteAllEmails(self, ids_to_delete):
        """ METHOD THAT DELETES EMAILS IN GMAIL INBOX BY IDS

        Args:
            ids_to_delete ([list]): LIST OF EMAIL IDS TO BE DELETED
        """

        try:

            if len(ids_to_delete) > 0:

                self.service.users().messages().batchDelete(userId='me', body={
                    "ids": ids_to_delete}).execute()

        except Exception:

            self.logger.ERROR()

    def extractSymbolsFromEmails(self, payloads):
        """ METHOD TAKES SUBJECT LINES OF THE EMAILS WITH THE SYMBOLS AND SCANNER NAMES AND EXTRACTS THE NEEDED THE INFO FROM THEM.

        Args:
            payloads ([list]): LIST OF EMAIL CONTENT

        Returns:
            [dict]: DICT OF EXTRACTED EMAIL CONTENT
        """

        title = None

        symbols_obj = {
            "EQUITY": [],
            "OPTION": []
        }

        def convertOption(symbol):

            symbol = symbol.replace(".", "").strip()

            ending_index = 0

            int_found = False

            for index, char in enumerate(symbol):

                try:

                    int(char)

                    int_found = True

                except:

                    if not int_found:

                        ending_index = index

            exp = symbol[ending_index + 1:]

            year = exp[:2]

            month = exp[2:4]

            day = exp[4:6]

            # .AA201211C5.5

            # AA_121120C5.5

            pre_symbol = f"{symbol[:ending_index + 1]}_{month}{day}{year}{exp[6:]}"

            return symbol[:ending_index + 1], pre_symbol, datetime.strptime(f"{year}-{month}-{day}", "%y-%m-%d")

        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY, 1h, EQUITY, PRIMARY
        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY, 1h, EQUITY, SECONDARY

        for payload in payloads:

            try:

                seperate = payload.split(":")

                if len(seperate) > 1:

                    contains = ["were added to", "was added to"]

                    for i in contains:

                        if i in seperate[2]:

                            sep = seperate[2].split(i)

                            symbols = sep[0].strip().split(",")

                            strategy, side, aggregation, asset_type, account_type = sep[1].strip().split(
                                ",")

                            account_type = account_type.replace(".", " ")

                            for symbol in symbols:

                                if strategy != "" and side != "" and aggregation != "" and asset_type != "" and account_type != "":

                                    obj = {
                                        "Side": side.upper().strip(),
                                        "Aggregation": aggregation.lower().strip(),
                                        "Strategy": strategy.replace(".", " ").strip(),
                                        "Asset_Type": asset_type.strip(),
                                        "Account_Type": account_type.strip()
                                    }

                                    if asset_type.strip() == "OPTION":

                                        symbol, pre_symbol, exp_date = convertOption(
                                            symbol)

                                        obj["Pre_Symbol"] = pre_symbol

                                        obj["Exp_Date"] = exp_date

                                    obj["Symbol"] = symbol.strip()

                                    symbols_obj[asset_type.strip()].append(obj)

                                else:

                                    self.logger.ERROR(
                                        f"MISSING FIELDS FOR STRATEGY {strategy}")

                            break

                    title = payload

                    self.logger.INFO(f"NEW EMAIL: {payload}")

            except Exception as e:

                exception_type = type(e).__name__

                if exception_type != "IndexError":

                    self.logger.ERROR()

            finally:

                # |ERROR| >>> Class: TDAmeritrade >>> Error: name 'client_id' is not defined >>> Date: 2020-08-07 16:53:39

                if title != None:

                    prevent_error = title.split(" ")[0].strip()

                    if prevent_error != "|ERROR|":

                        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

                        dt_central = dt.astimezone(pytz.timezone('US/Central'))

                        dt = datetime.strptime(dt_central.strftime(
                            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

                        self.emails.insert_one({
                            "Title": title,
                            "Date": dt
                        })

        return symbols_obj

    def getEmails(self):
        """ METHOD RETRIEVES EMAILS FROM INBOX, ADDS THEIR IDS TO ids_to_delete LIST, AND ADD THEIR CONTENT TO payloads LIST TO BE EXTRACTED.

        Returns:
            [dict]: DICT RETURNED FROM extractSymbolsFromEmails METHOD
        """

        ids_to_delete = []

        payloads = []

        try:

            results = self.service.users().messages().list(userId='me').execute()

            if results['resultSizeEstimate'] != 0:

                new_results_list = []

                # {'id': '173da9a232284f0f', 'threadId': '173da9a232284f0f'}
                for message in results["messages"]:

                    ids_to_delete.append(message["id"])

                    result = self.service.users().messages().get(
                        id=message["id"], userId="me", format="metadata").execute()

                    new_results_list.append(result)

                for email in new_results_list:

                    for payload in email['payload']["headers"]:

                        if payload["name"] == "Subject":

                            payloads.append(payload["value"].strip())
            
        except Exception:

            self.logger.ERROR()

        finally:

            if len(ids_to_delete) > 0:

                self.deleteAllEmails(ids_to_delete)

            return self.extractSymbolsFromEmails(payloads)
