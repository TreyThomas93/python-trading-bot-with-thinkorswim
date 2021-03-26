# Python Trading Bot w/ Thinkorswim

## Description

- This program is an automated trading bot that uses TDAmeritrades Thinkorswim trading platform's scanners and alerts system.

## Table Of Contents

- [How it works](#how-it-works)

- [Dependencies](#dependencies)

- [Setup](#setup)

  - [MongoDB](#mongo)
  - [Gmail](#gmail)
  - [Pushsafer](#pushsafer)
  - [TDA API Tokens](#tokens)
  - [Thinkorswim](#thinkorswim)

    - [Scanner Names](#scanner-names)
    - [Scanner Offset](#scanner-offset)
    - [Scanner Alerts](#alerts)

- [Results](#results)

- [Share Your Strategy Results](#share-your-strategy-results)

- [Discrepencies](#discrepencies)

- [What I Use and Costs](#what-i-use-and-costs)

- [Code Counter](#code-counter)

- [Final Thoughts and Support](#final-thoughts-and-support)

## <a name="how-it-works"></a> How it works (in a nutshell)

### Thinkorswim:

    1. USER CREATES STRATEGIES IN THINKORSWIM.
    2. USER THEN CREATES SCANNERS FOR THOSE STRATEGIES. (SCANNER NAME HAS SPECIFIC FORMAT)
    3. USER THEN SETS EMAIL ALERTS TO USER SPECIFIC GMAIL ADDRESS THAT IS SETUP THROUGH THE THINKORSWIM PROGRAM.
    4. WHEN NEW SYMBOL IS POPULATED INTO THE SCANNER, AN ALERT IS TRIGGERED, AND AN EMAIL IS SENT.

### Trading Bot:

    1. BOT CONTINUOUSLY SCANS GMAIL ACCOUNT, LOOKING FOR ALERTS.
    2. ONCE ALERTS ARE FOUND, BOT PICKS APART EMAIL INFO TO DETERMINE WHICH STOCKS NEED TO BUY/SELL FOR WHICH STRATEGY.

- You can only buy a stock once per strategy, but you can buy the same stock on multiple strategies. Unlimited shares, obviously. It's very diversified.

- MongoDB database stores and keeps track of all of your open and closed positions, along with other data. Completely seperated from TDAmeritrade.

- This is setup for both EQUITY and OPTIONS trading, but I have not traded OPTIONS on this as of yet.

- Program Flow Chart

  ![Program Flow Chart](assets/img/program_flow_chart.png)

## <a name="dependencies"></a> Dependencies

> [dev-packages]

- pylint
- bandit
- pandas
- tabulate

> [packages]

- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
- python-dotenv
- pymongo
- dnspython
- termcolor
- colorama
- requests
- pytz
- psutil

> [venv]

- pipenv

> [requires]

- python_version = "3.8"

## <a name="setup"></a> Setup

- Assuming that you already have a TDAmeritrade account and the Thinkorswim desktop application already downloaded, we will move on to the next step.

### <a name="mongo"></a> MONGODB

- Create a MongoDB [account](https://www.mongodb.com/), create a cluster, and create two databases with the following names:

  1. Live_Trader
  2. Sim_Trader

- The Live_Trader database will contain all the important data used for actual live trading.

- The Sim_Trader database will be used for simulated trading, basically buying and selling everything, regardless of buying power. Pretty much paper trading without going through the TDA api.

- You will need the mongo uri to be able to connect pymongo in the program. Store this uri in a .env file within your mongo package in your code.

- The images below shows the structure of how the databases and users collection is setup:

![Live Trader Database](assets/img/Live_Trader_Collections.png)

- Most of the Live_Trader collections are used to collect long term data for use on my front end web app I have developed, which is not public at this time.

- The most crucial collections are:

  1. users
  2. queue
  3. open_positions
  4. closed_positions
  5. other

- The users collection store all users and their individial data, such as name and accounts.

- The queue stores non-filled orders that are working or queued, until either cancelled or filled.

- The open_positions stores all open positions and is used to help determine if an order is warranted.

- The closed_positions stores all closed positions after a trade has completed.

- The other stores all rejected and cancelled orders. Rejected typically happens if not enough buying power, and I have it set to cancel buy orders that have been sitting in queue for 2 hours or more.

![Sim Trader Database](assets/img/Sim_Trader_Collections.png)

![Users Collection](assets/img/Users_Collection_Setup.png)

- The image above shows the structure of how a user is setup. In the Accounts object, the key is the account number, and the value is another object with all of that account info and the tokens. All of this will auto populate into the users collection once you create your API tokens for TDAmeritrade using this [repo](https://github.com/TreyThomas93/TDA-Token) here.

### <a name="gmail"></a> Gmail

- First off, it is best to create an additional and seperate Gmail account and not your personal account.

- Make sure that you are in the account that will be used to receive alerts from Thinkorswim.

- You will need to create and turn on Google Docs API.
  https://developers.google.com/docs/api/quickstart/python

- Once created, save the credentials.json file to the creds directory within your gmail package in the program. This will be converted to token.json. After that, you can delete the credentials.json file.

- Run the program to see if you connect to Gmail. You will be prompted to sign in to your account. Make sure you sign in with the account you will be using with Thinkorswim for the program. You may be given an Unverified Apps screen. If so, follow this:

  1. Click the advanced button bottom left.
  2. Click the Go to Quickstart (unsafe) button.
  3. Click Allow.
  4. Click Allow again.
  5. You then will be redirected to a callback of localhost with the message "The authentication flow has completed. You may close this window."
  6. Exit out, and you should be connected.

- Once verified, you may have to go to your Google Developers Portal to enable your app.

- Now you should be able to fully connect. If the token.json gets removed, you will not be able to connect.

- Let me know via email if you have issues, and I can help guide you through the process.

### <a name="pushsafer"></a> Pushsafer

- Pushsafer allows you to send and receive push notifications to your phone from the program.

- This is handy for knowing in real time when trades are placed.

- You can also receive error notifications, but I stopped that for now.

- The first thing you will need to do is register:
  https://www.pushsafer.com/

- Once registered, read the docs on how to register and connect to devices. There is an Android and IOS app for this.

- You will also need to pay for API calls, which is about $1 for 1,000 calls.

- You will also need to store your api key in your code in a .env file that is stored in your push_notification package.

### <a name="tokens"></a> TDAmeritrade API Tokens

- You will need an access token and refresh token for each account you wish to use.
- Here is my [repo](https://github.com/TreyThomas93/TDA-Token) to help you to get these tokens and save them to your mongo database, in your users collection.

### <a name="thinkorswim"></a> Thinkorswim

- If you are familiar with creating strategies and setting up scanners, then this part should be easy.
- There are some things that we need to make sure are done correctly, such as the following:
  1. Make sure the scanner names are formatted correctly so the program can use them.
  2. Make sure the scanner logic is setup correctly so the alerts trigger at the correct time.
  3. Make sure your alerts are set up correctly.

#### <a name="scanner-names"></a> Scanner Names

- The format for the scanner name should look like this: STRATEGY, SIDE, AGGREGATION, ASSET TYPE, ACCOUNT TYPE

- Example: ![Scanner Name Format](assets/img/Scanner_Name_Format.PNG)

  1. REVA is the strategy name.
  2. SELL is the side. Can be BUY, SELL, BUY_TO_OPEN, SELL_TO_CLOSE
  3. 4h is the aggregation. ex. 30m, 1h, 4h, D
  4. EQUITY is the asset type. Can be EQUITY OR OPTION
  5. PRIMARY is the account type. Can be PRIMARY, SECONDARY, ect.... (Subject to change to Day, Swing)

- Must be in this exact order and spelled correctly for this to work properly.

#### <a name="scanner-offset"></a> Scanner logic offset

- The scanners need to be offset by one in order to send a non-premature alert. It needs to look at the previous bar for whatever aggregation you have set for it. This will look at the last bar to see if it met criteria, and if so, triggers an alert. The reason for this is that if we used the current candle, and this is based on experience, the symbols will populate and then be removed constantly throughout that aggregation, and may not actually meet criteria by the end.

- This is how an entry strategy in the charts may look.

![Chart Strategy Example](assets/img/Chart_Strategy.PNG)

- This is how the scanner should look for the exact same entry strategy.

![Scanner Strategy Example](assets/img/Scanner_Strategy.PNG)

- The only thing that changed was that [1] was added to offset the scanner by one and to look at the previous candle.

#### <a name="alerts"></a> Setting up Alerts

- When setting up alerts, make sure you select to send an alert everytime a symbol is added, or this will not work.
- Also, make sure that the email box is checked to allow the alerts to be sent to your gmail.

### <a name="results"></a> Results

- I have been using this since October 2020, and without giving to much detail, I can vouch that it is profitable. That being said, everyone's experience will be different, and not everyone will share the same results.

- Obviously, results are based off of how good your strategies that are developed in Thinkorswim are.

#### Simulated Results

- These results are simulated, which means they bought and sold everytime an alert came through from the emails. This is basically paper trading, but through the program. It would represent what it would be like with no buying power limit. This is based off of 1 share trades. Most of these strategies have been running since October 2020. As you can see, the program is affective, but obviously results may vary depending on how good your strategies are and also how much money you have to trade with.

![Simulated Results](assets/img/sim_results.PNG)

### <a name="share-your-strategy-results"></a> Share Your Strategy Results!

- If you want to help contribute to the community by sharing your simulated strategy results with the world, then all you have to do is uncomment out the following block of code located in the sellOrder method in the SimTrader class in the code.

![Strategy Result Code](assets/img/send-strategy-result.PNG)

- Just insert your email address into the variable called email, and everytime a simulated position sells out, it will be sent to a server to be displayed in a web app.

- The web app will grade each strategy based on average ROV, profit loss, wins, losses, win rate percentage, max drawdown, and sharpe ratio.

- This is strictly **VOLUNTARY**.

- The web app url is https://605e52f13b173a0008e6efef--goofy-yonath-bdedbd.netlify.app/Dashboard

### <a name="discrepencies"></a> DISCREPENCIES

- This program is not perfect. I am not liable for any profits or losses.
- There are several factors that could play into the program not working correctly. Some examples below:

  1. TDAmeritrades API is buggy at times, and you may lose connection, or not get correct responses after making requests.
  2. Thinkorswim scanners update every 3-5 minutes, and sometimes symbols wont populate at a timely rate. I've seen some to where it took 20-30 minutes to finally send an alert.
  3. Gmail servers could go down aswell. That has happened in the past, but not very common.
  4. And depending on who you have hosting your server for the program, that is also subject to go down sometimes, either for maintenance or for other reasons.
  5. As for refreshing the refresh token, I have been running into issues when renewing it. The TDA API site says the refresh token will expire after 90 days, but for some reason It won't allow you to always renew it and may give you an "invalid grant" error, so you may have to play around with it or even recreate everything using this [repo](https://github.com/TreyThomas93/TDA-Token). Just make sure you set it to existing user in the script so it can update your account.

- The program is very indirect, and lots of factors play into how well it performs. For the most part, it does a great job.

### <a name="what-i-use-and-costs"></a> What I use and costs

> SERVER FOR HOSTING PROGRAM

- PythonAnywhere -- $7 / month

> DATABASE

- MongoDB Atlas -- Approx. $25 / month
- I currently use the M5 tier.

![Mongo Tiers](assets/img/cluster-tier.png)

> NOTIFICATION SYSTEM

- PushSafer -- Less than $5 / month

### <a name="code-counter"></a> CODE COUNTER

Total : 15 files, 2290 codes, 440 comments, 1239 blanks, all 3969 lines

#### Languages

| language | files |  code | comment | blank | total |
| :------- | ----: | ----: | ------: | ----: | ----: |
| Python   |    12 | 1,423 |     440 | 1,116 | 2,979 |
| JSON     |     1 |   650 |       0 |     1 |   651 |
| Markdown |     1 |   193 |       0 |   118 |   311 |
| toml     |     1 |    24 |       0 |     4 |    28 |

#### Directories

| path                     | files |  code | comment | blank | total |
| :----------------------- | ----: | ----: | ------: | ----: | ----: |
| .                        |    15 | 2,290 |     440 | 1,239 | 3,969 |
| assets                   |     5 |   111 |      43 |    92 |   246 |
| assets\exception_handler |     1 |    17 |       1 |    17 |    35 |
| assets\logger            |     1 |    50 |      36 |    44 |   130 |
| assets\push_notification |     1 |    37 |       5 |    24 |    66 |
| gmail                    |     1 |   147 |      36 |   120 |   303 |
| live_trader              |     1 |   304 |     103 |   218 |   625 |
| mongo                    |     1 |    33 |       0 |    30 |    63 |
| sim_trader               |     1 |   232 |      65 |   225 |   522 |
| tasks                    |     1 |   346 |      69 |   232 |   647 |
| tdameritrade             |     1 |   144 |      85 |   114 |   343 |

### <a name="final-thoughts-and-support"></a> FINAL THOUGHTS

- This is in continous development, with hopes to make this program as good as it can possibly get. I know this README might not do it justice with giving you all the information you may need, and you most likely will have questions. Therefore, don't hesitate to contact me either via Github or email. As for you all, I would like your input on how to improve this, and I also heavily encourage you to fork the code and send me your improvements. I appreciate all the support! Thanks, Trey.

- If you like backtesting with Thinkorswim, here's a [repo](https://github.com/TreyThomas93/TOS-Auto-Export) of mine that may help you export strategy reports alot faster.

- Also, If you like what I have to offer, please support me here!

> <a href="https://www.buymeacoffee.com/TreyThomas"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee?&emoji=&slug=TreyThomas&button_colour=604343&font_colour=ffffff&font_family=Inter&outline_colour=ffffff&coffee_colour=FFDD00"></a>
