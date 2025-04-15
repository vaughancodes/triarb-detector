import ccxt.async_support as ccxt
import time

async def fetch_tickers(exchange):
    tickers = await exchange.fetch_tickers() if exchange.has['fetchTickers'] else []
    return tickers
    
async def fetch_currencies(exchange):
    currencies = exchange.currencies if exchange.has['fetchCurrencies'] else {}
    return currencies

async def get_exchange_data(exchange_name):
    exchange_class = getattr(ccxt, exchange_name)
    exchange = exchange_class()
    try:
        tickers = await fetch_tickers(exchange)
        currencies = await fetch_currencies(exchange)
        exchange_time = exchange.milliseconds()
    finally:
        await exchange.close()  # Ensure we close the exchange connection to avoid stale data
    return tickers, currencies, exchange_time