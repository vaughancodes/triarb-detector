import json
import websockets

from utils.constants import currency_symbols
from utils.exchanges.exchange import ExchangeData

class CoinbaseExchangeData(ExchangeData):
    def __init__(self):
        super().__init__()
        self.fee_rate = 0.06
    
    async def retrieve_symbols_data(self, tickers, disable_intermediate_currencies=True):
        coinbase_url = "wss://ws-feed.exchange.coinbase.com"
        cb_fmt_tickers = []
        for key, _ in tickers.items():
            if disable_intermediate_currencies:
                if tickers[key]["symbol"].split("/")[0] in currency_symbols or tickers[key]["symbol"].split("/")[1] in currency_symbols:
                    continue
            cb_fmt_tickers.append(tickers[key]["symbol"].replace("/", "-"))
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": cb_fmt_tickers,
            "channels": ["ticker"]
        }
        #print("Receiving data from Coinbase...")
        async with websockets.connect(coinbase_url) as websocket:
            await websocket.send(json.dumps(subscribe_msg))
            async for message in websocket:
                message = json.loads(message)
                if "type" in message and message["type"] == "ticker":
                    ticker = message["product_id"].replace("-", "").lower()
                    self.symbol_prices[ticker] = {
                        "ask": message["best_ask"],
                        "bid": message["best_bid"]
                    }