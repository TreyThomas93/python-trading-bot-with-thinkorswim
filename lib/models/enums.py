from enum import Enum


class AssetType(Enum):
    EQUITY = "EQUITY"
    # OPTION = "OPTION"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    # STOP = "STOP"
    # STOP_LIMIT = "STOP_LIMIT"
    # TRAILING_STOP = "TRAILING_STOP"
    # MARKET_ON_CLOSE = "MARKET_ON_CLOSE"
    # EXERCISE = "EXERCISE"
    # TRAILING_STOP_LIMIT = "TRAILING_STOP_LIMIT"
    # NET_DEBIT = "NET_DEBIT"
    # NET_CREDIT = "NET_CREDIT"
    # NET_ZERO = "NET_ZERO"

class Session(Enum):
    NORMAL = "NORMAL"
    # SEAMLESS = "SEAMLESS"

class Duration(Enum):
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"
    DAY = "DAY"
    # FILL_OR_KILL = "FILL_OR_KILL"
    # IMMEDIATE_OR_CANCEL = "IMMEDIATE_OR_CANCEL"

class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"   
    # BUY_TO_COVER = "BUY_TO_COVER"
    # SELL_SHORT = "SELL_SHORT"
    # BUY_TO_OPEN = "BUY_TO_OPEN"
    # BUY_TO_CLOSE = "BUY_TO_CLOSE"
    # SELL_TO_OPEN = "SELL_TO_OPEN"
    # SELL_TO_CLOSE = "SELL_TO_CLOSE"
    # EXCHANGE = "EXCHANGE"

class TradeType(Enum):
    LIVE = "LIVE"
    PAPER = "PAPER"

class OrderStatus(Enum):
    QUEUED = "QUEUED"
    FILLED = "FILLED"