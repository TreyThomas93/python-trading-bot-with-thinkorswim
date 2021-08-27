# Python Trading Bot w/ Thinkorswim

## Description

- This program is an automated trading bot that uses TDAmeritrades Thinkorswim trading platform's scanners and alerts systems to place trades dynamically using the TDAmeritrade API.

- _ATTENTION:_ This branch is a simpler and grossly reduced version of the original branch. It allows for a very basic and simple code base to focus on the main components of the program. The main things removed from the program were methods that were used to collect data for a web app I created to display my program results. Therefore, it wasn't necessary for the program to work properly for it's intended purposes. I also removed the OPTIONS handler. You could always re-add these methods and functionality to your code. I also revised on how the scanner names are formated and removed unnecessary collections in Mongo, so please check out the rest of this updated README.

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

- This is setup for EQUITY only.

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

- The collections are:

  1. users
  2. queue
  3. open_positions
  4. closed_positions
  5. other

- The users collection stores all users and their individial data, such as name and accounts.

- The queue stores non-filled orders that are working or queued, until either cancelled or filled.

- The open_positions stores all open positions and is used to help determine if an order is warranted.

- The closed_positions stores all closed positions after a trade has completed.

- The other stores all rejected and cancelled orders. Rejected typically happens if not enough buying power, and I have it set to cancel buy orders that have been sitting in queue for 2 hours or more.

![Sim Trader Database](assets/img/Sim_Trader_Collections.png)

- The image above shows the structure of the sim_trader collection. Only open_positions and closed_positions are needed.

![Users Collection](assets/img/Users_Collection_Setup.png)

- The image above shows the structure of how a user is setup. In the Accounts object, the key is the account number, and the value is another object with all of that accounts info and the tokens. All of this will auto populate into the users collection once you create your API tokens for TDAmeritrade using this [repo](https://github.com/TreyThomas93/TDA-Token) here.

- _ATTENTION:_ I have grossly reduced the amount of data needed to be stored in these collections. I even reduced the amount of collections overall. I minimalized and cut out the unnecessary parts that only served to represent data within a web app I created. Therefore, the code is simpler and easier to break down. If you want to add more features and such, then you obviously can do so.

### <a name="gmail"></a> Gmail

- First off, it is best to create an additional and seperate Gmail account and not your personal account.

- Make sure that you are in the account that will be used to receive alerts from Thinkorswim.
- _Step by Step (Follow this to setup Gmail API):_

1. https://developers.google.com/gmail/api/quickstart/python
2. https://developers.google.com/workspace/guides/create-project
3. https://developers.google.com/workspace/guides/create-credentials
4. After you obtain your credentials file, make sure you rename it to credentials.json and store it in the creds folding within the gmail package in the program.
5. Run the program and you will go through the OAuth process. Once complete, a token.json file will be stored in your creds folder.
6. If you get an access_denied during the OAuth process, try this: https://stackoverflow.com/questions/65184355/error-403-access-denied-from-google-authentication-web-api-despite-google-acc

*ATTENTION:* Be advised that while your gmail api app that you create during the above process is in TESTING mode, the tokens will expire after 7 days. https://stackoverflow.com/questions/66058279/token-has-been-expired-or-revoked-google-oauth2-refresh-token-gets-expired-i 

- If anyone finds an easier way around this or a better way to go about the production process, please let me know.

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

- The format for the scanner name should look like this: STRATEGY, SIDE, ACCOUNT ID #1, ACCOUNT ID #2... ECT.

- Example: ![Scanner Name Format](assets/img/Scanner_Name_Format.PNG)

  1. REVA is the strategy name example.
  2. SELL is the side. Can be BUY or SELL
  3. ACCOUNT ID. ADD AS MANY ACCOUNT IDS THAT YOU WANT FROM HERE, FOLLOWED BY COMMAS OF COURSE. ALL OF THESE ACCOUNTS WILL RUN THIS PARTICULAR STRATEGY.

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

Total : 15 files, 1839 codes, 341 comments, 842 blanks, all 3022 lines

## Languages

| language | files | code | comment | blank | total |
| :------- | ----: | ---: | ------: | ----: | ----: |
| Python   |    12 |  923 |     341 |   709 | 1,973 |
| JSON     |     1 |  696 |       0 |     1 |   697 |
| Markdown |     1 |  196 |       0 |   128 |   324 |
| toml     |     1 |   24 |       0 |     4 |    28 |

## Directories

| path                     | files |  code | comment | blank | total |
| :----------------------- | ----: | ----: | ------: | ----: | ----: |
| .                        |    15 | 1,839 |     341 |   842 | 3,022 |
| assets                   |     5 |   116 |      43 |    97 |   256 |
| assets\exception_handler |     1 |    22 |       1 |    22 |    45 |
| assets\logger            |     1 |    50 |      36 |    44 |   130 |
| assets\push_notification |     1 |    37 |       5 |    24 |    66 |
| gmail                    |     1 |    95 |      31 |    78 |   204 |
| live_trader              |     1 |   243 |     104 |   164 |   511 |
| mongo                    |     1 |    36 |       1 |    32 |    69 |
| sim_trader               |     1 |    88 |       9 |    68 |   165 |
| tasks                    |     1 |   103 |      31 |    77 |   211 |
| tdameritrade             |     1 |   144 |      85 |   114 |   343 |

### <a name="final-thoughts-and-support"></a> FINAL THOUGHTS

- This is in continous development, with hopes to make this program as good as it can possibly get. I know this README might not do it justice with giving you all the information you may need, and you most likely will have questions. Therefore, don't hesitate to contact me either via Github or email. As for you all, I would like your input on how to improve this, and I also heavily encourage you to fork the code and send me your improvements. I appreciate all the support! Thanks, Trey.

- > _DISCORD GROUP_ - I have created a Discord group to allow for a more interactive enviroment that will allow for all of us to answer questions and talk about the program. <a href="https://discord.gg/ys5jWuSE">Discord Group</a>

- If you like backtesting with Thinkorswim, here's a [repo](https://github.com/TreyThomas93/TOS-Auto-Export) of mine that may help you export strategy reports alot faster.

- Also, If you like what I have to offer, please support me here!

> <a href="https://www.buymeacoffee.com/TreyThomas"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee?&emoji=&slug=TreyThomas&button_colour=604343&font_colour=ffffff&font_family=Inter&outline_colour=ffffff&coffee_colour=FFDD00"></a>
