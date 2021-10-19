

class OrderBuilder:

    def __init__(self):

        pass

    def standardOrder(self, trade_data, asset_type, order_type="LIMIT"):

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        order = {
            "orderType": order_type,
            "price": None,
            "session": "SEAMLESS" if asset_type == "EQUITY" else "NORMAL",
            "duration": "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": side,
                    "quantity": None,
                    "instrument": {
                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"],
                        "assetType": asset_type,
                    }
                }
            ]
        }

        return order

    def OCOorder(self, trade_data, asset_type, order_type="LIMIT"):

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        order = {
            "orderType": order_type,
            "price": None,
            "session": "SEAMLESS" if asset_type == "EQUITY" else "NORMAL",
            "duration": "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": side,
                    "quantity": None,
                    "instrument": {
                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"],
                        "assetType": asset_type,
                    }
                }
            ]
        }

        order["orderStrategyType"] = "TRIGGER"

        order["childOrderStrategies"] = [
            {
                "orderStrategyType": "OCO",
                "childOrderStrategies": [
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "LIMIT",
                        "price": None,
                        "orderLegCollection": [
                            {
                                "instruction": "SELL",
                                "quantity": None,
                                "instrument": {
                                    "assetType": "EQUITY",
                                    "symbol": symbol
                                }
                            }
                        ]
                    },
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "STOP",
                        "stopPrice": None,
                        "orderLegCollection": [
                            {
                                "instruction": "SELL",
                                "quantity": None,
                                "instrument": {
                                    "assetType": "EQUITY",
                                    "symbol": "XYZ"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
