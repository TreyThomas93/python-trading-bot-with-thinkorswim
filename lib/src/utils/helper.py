

from datetime import datetime
from src.models.enums import Duration, Session
from src.models.enums import OrderStatus, OrderType

from src.models.enums import TradeType, Side, AssetType


class Helper:

    @staticmethod
    def dateTimeToString(dt: datetime) -> str:
        if dt == None:
            return None

        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def stringToDateTime(dt: str) -> datetime:
        if dt == None:
            return None

        return datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def getTradeTypeEnum(value: str) -> TradeType:
        match value:
            case "LIVE":
                return TradeType.LIVE
            case "PAPER":
                return TradeType.PAPER

    @staticmethod
    def getSideEnum(value: str) -> Side:
        match value:
            case "BUY":
                return Side.BUY
            case "SELL":
                return Side.SELL

    @staticmethod
    def getAssetTypeEnum(value: str) -> AssetType:
        match value:
            case "EQUITY":
                return AssetType.EQUITY

    @staticmethod
    def getOrderStatusEnum(value: str) -> OrderStatus:
        match value:
            case "WORKING":
                return OrderStatus.WORKING
            case "FILLED":
                return OrderStatus.FILLED
            case "REJECTED":
                return OrderStatus.REJECTED
            case "CANCELED":
                return OrderStatus.CANCELED
            case "QUEUED":
                return OrderStatus.QUEUED
            case _:
                return None

    @staticmethod
    def getOrderTypeEnum(value: str) -> OrderType:
        match value:
            case "MARKET":
                return OrderType.MARKET
            case _:
                return OrderType.MARKET

    @staticmethod
    def getSessionEnum(value: str) -> Session:
        match value:
            case "NORMAL":
                return Session.NORMAL
            case _:
                return Session.NORMAL

    @staticmethod
    def getDurationEnum(value: str) -> Duration:
        match value:
            case "GOOD_TILL_CANCEL":
                return Duration.GOOD_TILL_CANCEL
            case _:
                return Duration.GOOD_TILL_CANCEL
