

from datetime import datetime, timedelta
from enum import Enum
from logging import Logger
import time
from src.services.database import Database
from src.models.user_model import User
from src.utils.helper import Helper
import requests
import urllib.parse as up


class Method(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class TDA(Database):

    def __init__(self, accountId: int, accountInfo: dict, logger: Logger, user: User) -> None:
        self.accountId = accountId
        self.accountInfo = accountInfo
        self.logger = logger
        self.user = user

        self.invalidCount = 0
        self.terminate = False

        self.header = {}

        self.baseUrl = "https://api.tdameritrade.com/v1"

        super().__init__()

    def connect(self) -> bool:
        self.logger.info(
            f"Connecting {self.user.name} to TDAmeritrade - ({Helper.modifiedAccountID(self.accountId)})", extra={'log': False})

        isValid = self.__checkTokenValidity()

        if isValid:
            self.logger.info(
                f"Connected {self.user.name} to TDAmeritrade - ({Helper.modifiedAccountID(self.accountId)})", extra={'log': False})
            return True
        else:
            self.logger.error(
                f"Failed to connect {self.user.name} to TDAmeritrade - ({Helper.modifiedAccountID(self.accountId)})", extra={'log': False})
            return False

    def __checkTokenValidity(self) -> bool:
        """ Checks if tda token is valid
        Returns:
            [boolean]: returns True if token is valid, False if not
        """

        accountInfo = self.user.accounts[str(self.accountId)]

        # ADD EXISTING TOKEN TO HEADER
        self.header.update({
            "Authorization": f"Bearer {accountInfo['access_token']}"})

        # CHECK IF ACCESS TOKEN NEEDS UPDATED
        age_sec = round(
            time.time() - accountInfo.get('created_at', 0))

        if age_sec >= accountInfo['expires_in'] - 60:

            self.logger.info(
                f"Account token expired - ({Helper.modifiedAccountID(self.accountId)}).  Getting new token.")

            token = self.__getNewTokens(accountInfo)

            if token:

                self.user.accounts[str(self.accountId)
                                   ]['expires_in'] = token['expires_in']
                self.user.accounts[str(self.accountId)
                                   ]['access_token'] = token['access_token']
                self.user.accounts[str(self.accountId)
                                   ]['created_at'] = time.time()
                self.updateUserAccountInfo(self.accountId, self.user)

                self.header.update({
                    "Authorization": f"Bearer {token['access_token']}"})
            else:
                return False

        # CHECK IF REFRESH TOKEN NEEDS UPDATED
        now = datetime.strptime(datetime.strftime(
            datetime.now().replace(microsecond=0), "%Y-%m-%d"), "%Y-%m-%d")

        refresh_exp = datetime.strptime(
            accountInfo.get('refresh_exp_date', datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")

        days_left = (refresh_exp - now).total_seconds() / 60 / 60 / 24

        if days_left <= 5:

            self.logger.info(
                f'Account refresh token near expiration - ({Helper.modifiedAccountID(self.accountId)}).  Getting new token.')

            token = self.__getNewTokens(
                accountInfo, refresh_type="Refresh Token")

            if token:
                self.user.accounts[str(
                    self.accountId)]['refresh_token'] = token['refresh_token']
                self.user.accounts[str(self.accountId)]['refresh_exp_date'] = (datetime.now().replace(
                    microsecond=0) + timedelta(days=90)).strftime("%Y-%m-%d")
                self.updateUserAccountInfo(self.accountId, self.user)
                self.header.update({
                    "Authorization": f"Bearer {token['access_token']}"})

            else:
                return False

        return True

    def __getNewTokens(self, accountInfo, refresh_type="Access Token"):
        """ Gets new tokens from TDAmeritrade
        Args:
            token ([dict]): TOKEN DATA (ACCESS TOKEN, REFRESH TOKEN, EXP DATES)
            refresh_type (str, optional): CAN BE EITHER Access Token OR Refresh Token. Defaults to "Access Token".
        Raises:
            Exception: IF RESPONSE STATUS CODE IS NOT 200
        Returns:
            [json]: NEW TOKEN DATA
        """

        data = {'grant_type': 'refresh_token',
                'refresh_token': accountInfo["refresh_token"],
                'client_id': self.user.clientId}

        if refresh_type == "Refresh Token":

            data["access_type"] = "offline"

        # print(f"REFRESHING TOKEN: {data} - TRADER: {self.user['Name']} - REFRESH TYPE: {refresh_type} - ACCOUNT ID: {self.accountId}")

        resp = requests.post(f'{self.baseUrl}/oauth2/token',
                             headers={
                                 'Content-Type': 'application/x-www-form-urlencoded'},
                             data=data)

        if resp.status_code != 200:

            msg = f"Error fetching new tokens - {resp.json()} - User: {self.user.name} - Refresh Type: {refresh_type} - Account ID: {Helper.modifiedAccountID(self.accountId)}"
            self.logger.error(msg)
            self.invalidCount += 1

            if self.invalidCount == 5:
                self.terminate = True
                msg = f"TDAmeritrade Instance Terminated - {resp.json()} - Refresh Type: {refresh_type} - Account ID: {Helper.modifiedAccountID(self.accountId)}"
                self.logger.error(msg)
            return

        self.invalidCount = 0
        self.terminate = False

        self.logger.info(
            f"Successfully refreshed tokens - User: {self.user.name} - Refresh Type: {refresh_type} - Account ID: {Helper.modifiedAccountID(self.accountId)}")

        return resp.json()

    def __sendRequest(self, url, method: Method = Method.GET, data=None):
        isValid = self.__checkTokenValidity()

        if isValid:
            match method:
                case Method.GET:
                    resp = requests.get(url, headers=self.header)
                    return resp.json()
                case Method.POST:
                    resp = requests.post(url, headers=self.header, json=data)
                    return resp
                case Method.DELETE:
                    resp = requests.delete(url, headers=self.header)
                    return resp
                case Method.PUT:
                    resp = requests.put(url, headers=self.header, json=data)
                    return resp
                case _:
                    raise Exception("Invalid Method")
        else:
            raise Exception("Invalid Token")

    def getAccountInfo(self):
        fields = up.quote("positions,orders")
        url = f"{self.baseUrl}/accounts/{self.accountId}?fields={fields}"
        return self.__sendRequest(url)

    def placeTDAOrder(self, data: dict) -> dict:
        url = f"{self.baseUrl}/accounts/{self.accountId}/orders"
        return self.__sendRequest(url, method=Method.POST, data=data)

    def getQuote(self, symbol: str) -> dict:
        url = f"{self.baseUrl}/marketdata/{symbol}/quotes"
        return self.__sendRequest(url)

    def getSpecificOrder(self, orderId: int) -> dict:
        url = f"{self.baseUrl}/accounts/{self.accountId}/orders/{orderId}"
        return self.__sendRequest(url)

    def getAvailableBalance(self):
        account = self.getAccountInfo()
        balance = account["securitiesAccount"]["initialBalances"]["cashAvailableForTrading"]
        return float(balance)

    def cancelOrder(self, orderId: int):
        url = f"{self.baseUrl}/accounts/{self.accountId}/orders/{orderId}"
        return self.__sendRequest(url, method=Method.DELETE)
