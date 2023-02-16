
"""
This script allows the user to fetch [access] and [refresh] tokens for their TDAmeritrade account.
Running this script will open a browser window and will auto login the user to their TDAmeritrade account.
From there, the user will receive a code via text message and will need to enter that code into the browser window.
The user can also answer a security question instead of inputting a code.
Once completed, the browser window will close and the token data will be included in the response from the server.
If the user is not found in the [users.conf] file, they will be added to the file with the token data for the specified account.
Else if they are found in the [users.conf] file, the token data for the specified account will be updated.

A creds.env file is required in the same directory as this script.
Add the following to the creds.env file:
NAME=Your Name
CLIENT_ID=Your Client ID
TDA_USERNAME=Your Username
TDA_PASSWORD=Your Password
ACCOUNT_ID=Your Account ID

Name is the name you want associated with the user object for this account.
Client id is the consumer key that you get from the [https://developer.tdameritrade.com/] website after creating an app.
Username and password are your TDAmeritrade username and password for the account you want to use.
Account id is the account id for the account you want to use.

Once the creds.env file is created and the variables are added, run this script and follow the instructions in the browser window.

The response from the server will look like this:
{
    "access_token": "+jDDAaqtpkogBqzg4RZn6RE7oCsmEvDkR5FoXQy+........",
    "refresh_token": "YVLe43c/X2jSZwgMblQBWnBc0W2MuELQ0suh+AVO..........",
    "scope": "PlaceTrades AccountAccess MoveMoney",
    "expires_in": 1800,
    "refresh_token_expires_in": 7776000,
    "token_type": "Bearer",
}

The access token will expire in 30 minutes. The refresh token will expire in 90 days. The refresh token will be used to get a new access token when the access token expires.

**You are allowed to have multiple accounts per user. To add another account, replace the username/password and account id in the creds.env file and run this script again.**
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv
from json_database import JsonDatabase
import requests
import time
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import urllib.parse as up
import traceback
import sys
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))) + '/lib/src/models')

from user_model import User

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
path = Path(THIS_FOLDER)

path_to_creds = f'{path}/creds.env'

if not os.path.exists(path_to_creds):
    f = open(path_to_creds, 'x')
    f.close()

env_loaded = load_dotenv(dotenv_path=path_to_creds, verbose=True)

if not env_loaded:
    raise Exception('No env variables found. Please add the following to the creds.env file in this directory: \nNAME=Your Name\nCLIENT_ID=Your Client ID\nTDA_USERNAME=Your Username\nTDA_PASSWORD=Your Password\nACCOUNT_ID=Your Account ID\n')


class TDATokens:

    def fetchTokenData(self, clientId: str, username: str, password: str, name: str, accountId: str):
        try:
            driver = webdriver.Chrome(service=Service(
                ChromeDriverManager().install()))
            client_id = clientId + '@AMER.OAUTHAP'

            url = 'https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=' + \
                up.quote("http://localhost:8080") + \
                '&client_id=' + up.quote(client_id)
 
            driver.get(url)
            driver.implicitly_wait(5)

            ubox = driver.find_element(value='username0')
            pbox = driver.find_element(value='password1')

            ubox.send_keys(username)
            pbox.send_keys(password)

            driver.find_element(value='accept').click()
            driver.find_element(value='accept').click()

            while True:
                try:
                    code = up.unquote(driver.current_url.split('code=')[1])
                    if code != '':
                        break
                    else:
                        time.sleep(2)
                except:
                    pass

            driver.close()

            resp = requests.post('https://api.tdameritrade.com/v1/oauth2/token',
                                 headers={
                                     'Content-Type': 'application/x-www-form-urlencoded'},
                                 data={'grant_type': 'authorization_code',
                                       'refresh_token': '',
                                       'access_type': 'offline',
                                       'code': code,
                                       'client_id': clientId,
                                       'redirect_uri': "http://localhost:8080"})

            if resp.status_code != 200:
                print('Unable to fetch tokens')

            with JsonDatabase('users', f'lib/src/data/users.conf') as db:
                user = None
                for u in db:
                    if u['clientId'] == clientId or u['name'] == name:
                        user = User.fromJson(u)
                        break

                data = resp.json()

                data['created_at'] = time.time()
                data['refresh_exp_date'] = (datetime.now().replace(
                    microsecond=0) + timedelta(days=90)).strftime("%Y-%m-%d")

                if user is None:
                    print('User not found in database. Adding...')
                    db.add_item({
                        "name": name,
                        "clientId": clientId,
                        "accounts": {
                            accountId: data
                        }
                    })
                else:
                    print('User found in database. Updating...')
                    user.accounts[accountId] = data
                    db.add_item(user.toJson())

        except Exception:
            print(traceback.format_exc())


tokens = TDATokens()

tokens.fetchTokenData(name=os.getenv('NAME'),
                      clientId=os.getenv('CLIENT_ID'),
                      username=os.getenv('TDA_USERNAME'),
                      password=os.getenv('TDA_PASSWORD'),
                      accountId=os.getenv('ACCOUNT_ID')
                      )