# Python Trading Bot w/ Thinkorswim

## Description

- This automated trading bot utilizes TDAmeritrades API, Thinkorswim Alert System, Gmail API , and MongoDB to place trades, both Equity and Options, dynamically.

## <a name="how-it-works"></a> How it works (in a nutshell)

### Thinkorswim

1. Develop strategies in Thinkorswim.
2. Create a scanner for your strategy. (Scanner name will have specific format needed)
3. Set your scanner to send alerts to your non-personal gmail.
4. When a symbol is populated into the scanner, an alert is triggered and sent to gmail.

### Trading Bot (Python)

1. Continuously scrapes email inbox looking for alerts.
2. Once found, bot will extract needed information and will place a trade if warranted.

---

- You can only buy a symbol once per strategy, but you can buy the same symbol on multiple strategies.

- For Example:

1. > You place a buy order for AAPL with the strategy name MyRSIStrategy. Once the order is placed and filled, it is pushed to mongo.
2. > If another alert is triggered for AAPL with the strategy name of MyRSIStrategy, the bot will reject it because it's already an open position.
3. > Once the position is removed via a sell order, then AAPL with the strategy name of MyRSIStrategy can be bought again.

---

##  Getting Started

### Thinkorswim

1. Create a strategy that you want to use in the bot.
2. 