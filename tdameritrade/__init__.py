# imports
from datetime import datetime, timedelta
import urllib.parse as up
import platform
import os
import pytz
import time
import requests
import json
from assets.exception_handler import exception_handler


class TDAmeritrade:

    def __init__(self, mongo, user, account_id, logger):

        self.user = user

        self.account_id = account_id

        self.logger = logger

        self.users = mongo.users

        self.no_go_token_sent = False

        self.client_id = self.user["ClientID"]

        self.header = {}

        self.terminate = False

        self.invalid_count = 0

    @exception_handler
    def initialConnect(self):

        self.logger.INFO(
            f"CONNECTING {self.user['Name']} TO TDAMERITRADE ({self.account_id})")

        isValid = self.checkTokenValidity()

        if isValid:

            self.logger.INFO(
                f"CONNECTED {self.user['Name']} TO TDAMERITRADE ({self.account_id})\n")

            return True

        else:

            self.logger.CRITICAL(
                f"FAILED TO CONNECT {self.user['Name']} TO TDAMERITRADE ({self.account_id})")

            return False

    @exception_handler
    def getDatetime(self):

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_central = dt.astimezone(pytz.timezone('US/Central'))

        return datetime.strptime(dt_central.strftime(
            "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

    @exception_handler
    def checkTokenValidity(self):
        """ METHOD CHECKS IF ACCESS TOKEN IS VALID

        Returns:
            [boolean]: TRUE IF SUCCESSFUL, FALSE IF ERROR
        """

        # GET USER DATA
        user = self.users.find_one({"Name": self.user["Name"]})

        # ADD EXISTING TOKEN TO HEADER
        self.header.update({
            "Authorization": f"Bearer {user['Accounts'][self.account_id]['access_token']}"})

        # CHECK IF ACCESS TOKEN NEEDS UPDATED
        age_sec = round(
            time.time() - user["Accounts"][self.account_id]["created_at"])

        if age_sec >= user["Accounts"][self.account_id]['expires_in'] - 60:

            token = self.getNewTokens(user["Accounts"][self.account_id])

            if token:
                
                # ADD NEW TOKEN DATA TO USER DATA IN DB
                self.users.update_one({"Name": self.user["Name"]}, {
                    "$set": {f"Accounts.{self.account_id}.expires_in": token['expires_in'], f"Accounts.{self.account_id}.access_token": token["access_token"], f"Accounts.{self.account_id}.created_at": time.time()}})

                self.header.update({
                    "Authorization": f"Bearer {token['access_token']}"})

            else:

                return False

        # CHECK IF REFRESH TOKEN NEEDS UPDATED
        now = datetime.strptime(datetime.strftime(
            datetime.now().replace(microsecond=0), "%Y-%m-%d"), "%Y-%m-%d")

        refresh_exp = datetime.strptime(
            user["Accounts"][self.account_id]["refresh_exp_date"], "%Y-%m-%d")

        days_left = (refresh_exp - now).total_seconds() / 60 / 60 / 24

        if days_left == 1:
            
            token = self.getNewTokens(
                user["Accounts"][self.account_id], refresh_type="Refresh Token")

            if token:

                # ADD NEW TOKEN DATA TO USER DATA IN DB
                self.users.update_one({"Name": self.user["Name"]}, {
                    "$set": {f"{self.account_id}.refresh_token": token['refresh_token'], f"{self.account_id}.refresh_exp_date": (datetime.now().replace(
                        microsecond=0) + timedelta(days=90)).strftime("%Y-%m-%d")}})

                self.header.update({
                    "Authorization": f"Bearer {token['access_token']}"})

            else:

                return False

        return True

    @exception_handler
    def getNewTokens(self, token, refresh_type="Access Token"):
        """ METHOD GETS NEW ACCESS TOKEN, OR NEW REFRESH TOKEN IF NEEDED.

        Args:
            token ([dict]): TOKEN DATA (ACCESS TOKEN, REFRESH TOKEN, EXP DATES)
            refresh_type (str, optional): CAN BE EITHER Access Token OR Refresh Token. Defaults to "Access Token".

        Raises:
            Exception: IF RESPONSE STATUS CODE IS NOT 200

        Returns:
            [json]: NEW TOKEN DATA
        """
            
        data = {'grant_type': 'refresh_token',
                'refresh_token': token["refresh_token"],
                'client_id': self.client_id}

        if refresh_type == "Refresh Token":

            data["access_type"] = "offline"

        # print(f"REFRESHING TOKEN: {data} - TRADER: {self.user['Name']} - REFRESH TYPE: {refresh_type} - ACCOUNT ID: {self.account_id}")

        resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                                headers={
                                    'Content-Type': 'application/x-www-form-urlencoded'},
                                data=data)

        if resp.status_code != 200:

            if not self.no_go_token_sent:

                msg = f"ERROR WITH GETTING NEW TOKENS - {resp.json()} - TRADER: {self.user['Name']} - REFRESH TYPE: {refresh_type} - ACCOUNT ID: {self.account_id}"

                self.logger.ERROR(msg)

                self.no_go_token_sent = True

            self.invalid_count += 1

            if self.invalid_count == 5:

                self.terminate = True

                msg = f"TDAMERITRADE INSTANCE TERMINATED - {resp.json()} - TRADER: {self.user['Name']} - REFRESH TYPE: {refresh_type} - ACCOUNT ID: {self.account_id}"

                self.logger.ERROR(msg)

            return

        self.no_go_token_sent = False

        self.invalid_count = 0

        self.terminate = False

        return resp.json()

    @exception_handler
    def sendRequest(self, url, method="GET", data=None):
        """ METHOD SENDS ALL REQUESTS FOR METHODS BELOW.

        Args:
            url ([str]): URL for the particular API
            method (str, optional): GET, POST, PUT, DELETE. Defaults to "GET".
            data ([dict], optional): ONLY IF POST REQUEST. Defaults to None.

        Returns:
            [json]: RESPONSE DATA
        """

        isValid = self.checkTokenValidity()

        if isValid:

            if method == "GET":

                resp = requests.get(url, headers=self.header)

                return resp.json()

            elif method == "POST":

                resp = requests.post(url, headers=self.header, json=data)

                return resp

            elif method == "PATCH":

                resp = requests.patch(url, headers=self.header, json=data)

                return resp

            elif method == "PUT":

                resp = requests.put(url, headers=self.header, json=data)

                return resp

            elif method == "DELETE":

                resp = requests.delete(url, headers=self.header)

                return resp

        else:

            return

    def getAccount(self):
        """ METHOD GET ACCOUNT DATA

        Returns:
            [json]: ACCOUNT DATA
        """

        fields = up.quote("positions,orders")

        url = f"https://api.tdameritrade.com/v1/accounts/{self.account_id}?fields={fields}"

        return self.sendRequest(url)

    def placeTDAOrder(self, data):
        """ METHOD PLACES ORDER

        Args:
            data ([dict]): ORDER DATA

        Returns:
            [json]: ORDER RESPONSE INFO. USED TO RETRIEVE ORDER ID.
        """

        url = f"https://api.tdameritrade.com/v1/accounts/{self.account_id}/orders"

        return self.sendRequest(url, method="POST", data=data)

    def getBuyingPower(self):
        """ METHOD GETS BUYING POWER

        Returns:
            [json]: BUYING POWER
        """

        account = self.getAccount()

        buying_power = account["securitiesAccount"]["initialBalances"]["cashAvailableForTrading"]

        return float(buying_power)

    def getQuote(self, symbol):
        """ METHOD GETS MOST RECENT QUOTE FOR STOCK

        Args:
            symbol ([str]): STOCK SYMBOL

        Returns:
            [json]: STOCK QUOTE
        """

        url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/quotes"

        return self.sendRequest(url)

    def getQuotes(self, symbols):
        """ METHOD GETS STOCK QUOTES FOR MULTIPLE STOCK IN ONE CALL.

        Args:
            symbols ([list]): LIST OF SYMBOLS

        Returns:
            [json]: ALL SYMBOLS STOCK DATA
        """

        join_ = ",".join(symbols)

        seperated_values = up.quote(join_)

        url = f"https://api.tdameritrade.com/v1/marketdata/quotes?symbol={seperated_values}"

        return self.sendRequest(url)

    def getSpecificOrder(self, id):
        """ METHOD GETS A SPECIFIC ORDER INFO

        Args:
            id ([int]): ORDER ID FOR ORDER

        Returns:
            [json]: ORDER DATA
        """

        url = f"https://api.tdameritrade.com/v1/accounts/{self.account_id}/orders/{id}"

        return self.sendRequest(url)

    def cancelOrder(self, id):
        """ METHOD CANCELS ORDER

        Args:
            id ([int]): ORDER ID FOR ORDER

        Returns:
            [json]: RESPONSE. LOOKING FOR STATUS CODE 200,201   
        """

        url = f"https://api.tdameritrade.com/v1/accounts/{self.account_id}/orders/{id}"

        return self.sendRequest(url, method="DELETE")
