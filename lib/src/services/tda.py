

from datetime import datetime, timedelta
from logging import Logger
from random import randint
import time
from src.services.database import Database
from src.models.user_model import User
from src.utils.helper import Helper
import requests


class TDA(Database):

    def __init__(self, accountId: int, accountInfo: dict, logger: Logger, user: User) -> None:
        self.accountId = accountId
        self.accountInfo = accountInfo
        self.logger = logger
        self.user = user

        self.invalidCount = 0
        self.terminate = False

        self.header = {}

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
            time.time() - accountInfo.get('created_at', time.time()))

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

        resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
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

    def placeTDAOrder(self) -> dict:
        return {}

    def getQuote(self, symbol: str) -> dict:
        return {symbol: {"lastPrice": randint(1.00, 100.00)}}

    def getSpecificOrder(self, orderId: int) -> dict:
        return {
            'orderId': orderId,
            'status': 'FILLED',
            'price': randint(1.00, 100.00),
        }
