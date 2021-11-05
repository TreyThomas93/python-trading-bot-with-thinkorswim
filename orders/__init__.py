def Standard_Order(price, side, quantity, symbol, asset_type):
        """ STANDARD BUY/SELL LIMIT ORDER
        """
            order = {
                "orderType": "LIMIT",
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


def Trailing_Stop_Order(price, side, quantity, symbol, asset_type, stopPriceOffset):
        """ STANDARD LIMIT ORDER WITH A TRAILING STOP SELL ORDER SET AT A DEFAULT 10%
        """
            order =   {
                    "orderType": "Limit",
                    "session": "Normal",
                    "price": None,
                    "duration": "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY",
                    "orderStrategyType": "TRIGGER",
                    "orderLegCollection": [
                        {
                            "instruction": side,
                            "quantity": None,
                            "instrument": {
                                "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"],
                                "assetType": asset_type
                                          }
                        }
                    ],
                    "childOrderStrategies": [
                        {
                            "session": "NORMAL",
                            "orderType": "TRAILING_STOP",
                            "stopPriceLinkBasis": "ASK",
                            "stopPriceLinkType": "PERCENT",
                            "stopPriceOffset": None,
                            "duration": "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY",
                            "orderStrategyType": "SINGLE",
                            "orderLegCollection": [
                                {
                                    "instruction": "SELL" if asset_type == "EQUITY" else "SELL_TO_CLOSE",
                                    "quantity": None,
                                    "instrument": {
                                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"],
                                        "assetType": asset_type
                                                  }
                                }
                                ]
                        }
                    ]
                    }

def OCO_Order(price, side, quantity, symbol, asset_type, stopPrice):
        """ STANDARD LIMIT ORDER WITH AN AUTOMATIC STOP LOSS AT 11% AND TAKE PROFIT PERCENTAGE AT 25%
        """
            order =   {
                      "orderStrategyType": "TRIGGER",
                      "session": "NORMAL",
                      "duration": "GOOD_TILL_CANCEL",
                      "orderType": "LIMIT",
                      "price": None,
                      "orderLegCollection": [{
                                          "instruction": side,
                                          "quantity": None,
                                          "instrument": {
                                                        "assetType": asset_type,
                                                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"] }
                                            }],
                      "childOrderStrategies": [{
                                          "orderStrategyType": "OCO",
                                          "childOrderStrategies": [
                                                                  {"orderStrategyType": "SINGLE",
                                                                  "session": "NORMAL",
                                                                  "duration": "GOOD_TILL_CANCEL",
                                                                  "orderType": "LIMIT",
                                                                  "price": None,
                                                                  "orderLegCollection": [{
                                                                                      "instruction": "SELL" if asset_type == "EQUITY" else "SELL_TO_CLOSE",
                                                                                      "quantity": None,
                                                                                      "instrument": {
                                                                                                    "assetType": asset_type,
                                                                                                    "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"], }}]},
                                                                  {"orderStrategyType": "SINGLE",
                                                                  "session": "NORMAL",
                                                                  "duration": "GOOD_TILL_CANCEL",
                                                                  "orderType": "STOP",
                                                                  "stopPrice": None,
                                                                  "orderLegCollection": [{
                                                                                          "instruction": "SELL" if asset_type == "EQUITY" else "SELL_TO_CLOSE",
                                                                                          "quantity": None,
                                                                                          "instrument": {
                                                                                                        "assetType": asset_type,
                                                                                                        "symbol": symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"], }
                                                                                        }]
                                                                  }
                                                                  ]
                                              }]
                      }