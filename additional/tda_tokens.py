

from datetime import datetime, timedelta
import os
from pathlib import Path
from dotenv import load_dotenv
from json_database import JsonDatabase
import requests
import time
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
            driver = webdriver.Chrome(ChromeDriverManager().install())
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

        except Exception:
            print(traceback.format_exc())


tokens = TDATokens()

tokens.fetchTokenData(name=os.getenv('NAME'),
                      clientId=os.getenv('CLIENT_ID'),
                      username=os.getenv('TDA_USERNAME'),
                      password=os.getenv('TDA_PASSWORD'),
                      accountId=os.getenv('ACCOUNT_ID')
                      )

# Database().addUser(User(
#     clientId=123456789,
#     accounts={
#         '123456789': 'ABC123',
#     },
#     name='John Doe',
# ))

# Database().addUser(User.fromJson({
#     "name": "John Doe",
#     "clientId": 'J45FF8V8435THD',
#     "accounts": {
#         "23465":
#                 {'access_token': 'jsdkgsjkdfgjkjdk', 'scope': 'PlaceTrades AccountAccess MoveMoney',
#                     'expires_in': 1800, 'refresh_token_expires_in': 7776000, 'token_type': 'Bearer'}

#     }
# }))
