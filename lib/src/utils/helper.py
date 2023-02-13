

from datetime import datetime

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
            
