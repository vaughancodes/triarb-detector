import json
import websockets
import requests
import time

from utils.constants import currency_symbols
from utils.exchanges.exchange import ExchangeData

import logging

# Configure the logger
logging.basicConfig(
    filename='app.log', 
    level=logging.ERROR, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class KucoinData(ExchangeData):
    def __init__(self):
        super().__init__()
        self.fee_rate = 0.01
    
    async def retrieve_symbols_data(self, tickers, disable_intermediate_currencies=True):
        token_response = requests.post("https://api.kucoin.com/api/v1/bullet-public")
        token_response_data = json.loads(token_response.text)
        token = token_response_data["data"]["token"]
        kucoin_url = token_response_data["data"]["instanceServers"][0]["endpoint"]

        all_symbols = []
        symbols_response = requests.get("https://api.kucoin.com/api/v2/symbols")
        symbols_response_data = json.loads(symbols_response.text)["data"]
        for symbol_data in symbols_response_data:
            all_symbols.append(symbol_data["symbol"])
        
        sub_msg_template = {
            "type": "subscribe",
            "response": True
        }
        sub_msgs = []
        topic = "/market/level2:"
        i = 0
        for key, _ in tickers.items():
            if disable_intermediate_currencies:
                if tickers[key]["symbol"].split("/")[0] in currency_symbols or tickers[key]["symbol"].split("/")[1] in currency_symbols:
                    continue
            if tickers[key]["symbol"].replace("/","-") not in all_symbols:
                continue
            topic += tickers[key]["symbol"].replace("/","-") + ","
            i += 1
            if i > 98:
                sub_msg = sub_msg_template
                topic = topic.rstrip(",")
                sub_msg["topic"] = topic
                sub_msgs.append(sub_msg)
                topic = "/market/level2:"
                i = 0

        req_id = None
        sent_subs = False
        async with websockets.connect(f"{kucoin_url}?token={token}") as websocket:
            async for message in websocket:
                message = json.loads(message)
                if "type" in message:
                    if message["type"] == "welcome":
                        req_id = message["id"]
                        if not sent_subs:
                            sent_subs = True
                            for sub_msg in sub_msgs:
                                sub_msg["id"] = req_id
                                await websocket.send(json.dumps(sub_msg))
                    if message["type"] == "message":
                        if message["subject"] == "trade.l2update":
                            ticker = message["topic"].split(":")[1].replace("-","").lower()
                            ask_price = bid_price = 0
                            if ticker in self.symbol_prices:
                                ask_price = self.symbol_prices[ticker]["ask"]
                                bid_price = self.symbol_prices[ticker]["bid"]
                            if len(message["data"]["changes"]["asks"]) > 0:
                                ask_price = message["data"]["changes"]["asks"][0][0]
                            if len(message["data"]["changes"]["bids"]) > 0:
                                bid_price = message["data"]["changes"]["bids"][0][0]
                            self.symbol_prices[ticker] = {
                                "ask": ask_price,
                                "bid": bid_price
                            }