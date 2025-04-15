import json
import websockets

from utils.constants import currency_symbols
from utils.exchanges.exchange import ExchangeData

class BinanceUSData(ExchangeData):
    def __init__(self):
        super().__init__()
        self.fee_rate = 0.057
    
    async def retrieve_symbols_data(self, tickers, disable_intermediate_currencies=True):
        binanceus_url = "wss://stream.binance.us:9443/stream?streams=btcusdt@depth5"
        for key, _ in tickers.items():
            if disable_intermediate_currencies:
                if any(curr_symbol == tickers[key]["info"]["symbol"] for curr_symbol in currency_symbols):
                    continue
            ws_symbol = tickers[key]["info"]["symbol"].lower()
            binanceus_url += "/"+ws_symbol+"@depth5"
        #print("Receiving data from Binance US...")
        async with websockets.connect(binanceus_url) as websocket:
            async for message in websocket:
                message = json.loads(message)
                if "data" in message:
                    ticker = message["stream"].split("@")[0]
                    self.symbol_prices[ticker] = {
                        "ask": message["data"]["asks"][0][0],
                        "bid": message["data"]["bids"][0][0]
                    }