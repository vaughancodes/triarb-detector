import json
import websockets

from utils.constants import currency_symbols
from utils.exchanges.exchange import ExchangeData

class CryptoComData(ExchangeData):
    def __init__(self):
        super().__init__()
        self.fee_rate = 0.075
    
    async def retrieve_symbols_data(self, tickers, disable_intermediate_currencies=True):
        cryptocom_url = "wss://ws.kraken.com/v2"
        cc_fmt_tickers = []
        for key, _ in tickers.items():
            if disable_intermediate_currencies:
                if tickers[key]["symbol"].split("/")[0] in currency_symbols or tickers[key]["symbol"].split("/")[1] in currency_symbols:
                    continue
            cc_fmt_tickers.append(tickers[key]["symbol"])
        subscribe_msg = {
            "method": "subscribe",
            "params": {
                "channel": "ticker",
                "symbol": cc_fmt_tickers
            }
        }
        async with websockets.connect(cryptocom_url) as websocket:
            await websocket.send(json.dumps(subscribe_msg))
            async for message in websocket:
                message = json.loads(message)
                if "channel" in message and message["channel"] == "ticker" and "data" in message:
                    for symbol_info in message["data"]:
                        ticker = symbol_info["symbol"].replace("/", "").lower()
                        self.symbol_prices[ticker] = {
                            "ask": symbol_info["ask"],
                            "bid": symbol_info["bid"]
                        }