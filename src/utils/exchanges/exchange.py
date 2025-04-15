import json
import websockets
            

class ExchangeData():
    def __init__(self):
        self.symbol_prices = {}
        self.all_symbols = []
        self.currencies = {}
        
        # retrieve_symbol_data is a function that will be overwritten by the child class
        # to handle the incoming messages from the websocket and update the symbol_prices
        self.retrieve_symbol_data = None
        
        # fee_rate is a value that is set individually per child class
        self.fee_rate = 0.0
    
    def get_symbol_ask(self, symbol):
        return self.symbol_prices[symbol]["ask"]
    
    def get_symbol_bid(self, symbol):
        return self.symbol_prices[symbol]["bid"]
    
    def is_symbol_in_data(self, symbol):
        return symbol in self.symbol_prices
    
