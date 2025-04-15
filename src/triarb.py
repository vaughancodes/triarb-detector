# pylint: disable=W0702, C0325
import os
import asyncio
import datetime
import copy
import ccxt.async_support as ccxt
from typing import List, Tuple
from dataclasses import dataclass
from threading import Thread
import websockets, json, time, random
import networkx as nx
import curses

import octobot_commons.symbols as symbols
import octobot_commons.constants as constants

from utils.ccxt import get_exchange_data
from utils.graph import find_all_rotations, ShortTicker
from utils.exchanges.binanceus import BinanceUSData
from utils.exchanges.coinbaseexchange import CoinbaseExchangeData
from utils.exchanges.cryptocom import CryptoComData
from utils.exchanges.kucoin import KucoinData

exchange_data_classes = {
    "binanceus": BinanceUSData,
    "coinbaseexchange": CoinbaseExchangeData,
    "cryptocom": CryptoComData,
    "kucoin": KucoinData
}

def get_arbitrage_cycles(base_currency: str, all_exchange_tickers: dict, min_cycle: int = 3, max_cycle: int = 5) -> Tuple[List[ShortTicker]]:
    # Build a directed graph of currencies
    graph = nx.DiGraph()

    for exchange_name in all_exchange_tickers:
        for ticker in all_exchange_tickers[exchange_name]:
            #print(ticker)
            if ticker.endswith("/USD") or ticker.startswith("USD/") or ticker.endswith("USD4") or ticker.endswith("USD"):
                continue
            ticker_parts = ticker.split("/")
            base = ticker_parts[0]
            quote = ticker_parts[1]
            graph.add_edge(base, quote, exchange_name=exchange_name)
            graph.add_edge(quote, base, exchange_name=exchange_name)

    cycles = []
    # Find all cycles in the graph with a length <= max_cycle
    for cycle in nx.simple_cycles(graph, length_bound=max_cycle):
        #print(cycle)
        if len(cycle) > max_cycle or len(cycle) < min_cycle:
            continue  # Skip cycles longer than max_cycle or shorter than min_cycle
        rotations = find_all_rotations(cycle)
        for rotation in rotations:
            if rotation[0] == base_currency:  # Get cycles that start with base currency
                cycles.append(rotation)
    return cycles


def get_best_opportunity(arbitrage_cycles: list, originating_exchange: str, exchanges_data: dict, transaction_fee: float = 0.0057) -> Tuple[List[ShortTicker], float]:
    best_profit = 0
    best_cycle_rates = []
    #for exchange_name in exchanges_data:
        #print(f"{exchange_name}: {exchanges_data[exchange_name].symbol_prices}")
    for cycle in arbitrage_cycles:
        profit = 1
        # Calculate the profits along the cycle
        cycle_rates = []
        previous_exchange = originating_exchange
        for i, base in enumerate(cycle):
            reversed = False
            quote = cycle[(i + 1) % len(cycle)]  # Wrap around to complete the cycle
            original_ticker_key = f"{base}/{quote}"
            #print(f"Checking {ticker_key}...")
            ticker_key = f"{base}{quote}".lower()
            reversed_ticker_key = f"{quote}{base}".lower()
            best_rate = 0
            best_exchange = None
            for exchange_name in exchanges_data:
                if i == 0 or i == len(cycle) - 1:
                    if exchange_name != originating_exchange:
                        continue
                if exchanges_data[exchange_name].is_symbol_in_data(ticker_key):
                    rate = float(exchanges_data[exchange_name].get_symbol_bid(ticker_key))
                    if previous_exchange != exchange_name:
                        pass
                    if rate > best_rate:
                        best_rate = rate
                        best_exchange = exchange_name
                elif exchanges_data[exchange_name].is_symbol_in_data(reversed_ticker_key):
                    rate = float(exchanges_data[exchange_name].get_symbol_ask(reversed_ticker_key))
                    if rate > 0:    # Protect against divide-by-zeros
                        rate = 1 / float(exchanges_data[exchange_name].get_symbol_ask(reversed_ticker_key))
                    if previous_exchange != exchange_name:
                        pass
                    if rate > best_rate:
                        best_rate = rate
                        best_exchange = exchange_name
                        reversed = True
            if not best_exchange:
                #print(f"Could not find {ticker_key} on any {exchange_name}")
                profit = 0
            if best_rate == 0:
                profit = 0
            previous_exchange = best_exchange
            profit *= best_rate * (1 - transaction_fee)
            cycle_rates.append((original_ticker_key, best_rate, best_exchange, reversed))
        #if profit != 0:
                #print(f"Found rate {best_rate} for {original_ticker_key} on {best_exchange}")

        if profit > best_profit:
            best_profit = profit
            best_cycle_rates = cycle_rates
    #print(f"Finished checking all cycles.")
    for exchange_name in exchanges_data:
        if len(exchanges_data[exchange_name].symbol_prices) == 0:
            print(f"No data for {exchange_name}...")

    return best_cycle_rates, best_profit



async def main(stdscr):
    # Initialize curses
    curses.curs_set(0)  # Hide the cursor
    stdscr.nodelay(1)   # Non-blocking input
    stdscr.timeout(100)  # Refresh every 100 ms

    loop = asyncio.get_event_loop()

    ## CONFIGURATION SECTION
    check_period = 0.1  # Check for arbitrage opportunities at this period length (in seconds)
    originating_exchange = "kucoin"
    other_exchanges = ["coinbaseexchange","binanceus"]
    
    exchanges = copy.deepcopy(other_exchanges)
    exchanges.insert(0,originating_exchange)
    exchanges_data = {}
    all_tickers = {}
    
    i = 0
    stdscr.clear()
    for exchange_name in exchanges:
        exchanges_data[exchange_name] = exchange_data_classes[exchange_name]()
        initial_tickers, currencies, exchange_time = await get_exchange_data(exchange_name)
        all_tickers[exchange_name] = initial_tickers
        #exchanges_data[exchange_name].currencies = currencies
        create_msg = f"Creating retrieval task for {exchange_name}..."
        stdscr.addstr(i, 0, create_msg)
        stdscr.refresh()
        loop.create_task(
            exchanges_data[exchange_name].retrieve_symbols_data(
                tickers=all_tickers[exchange_name]
            )
        )
        i += 1
    
    arbitrage_cycles = get_arbitrage_cycles(base_currency="USDT", all_exchange_tickers=all_tickers)

    current_rates = {}
    start_time = time.monotonic()
    
    stdscr.clear()
    stdscr.addstr(i+2, 0, "Waiting for all symbol prices to be initialized...")
    exchange_data_ready = False
    while not exchange_data_ready:
        ready = True
        for exchange_name in exchanges:
            if len(exchanges_data[exchange_name].symbol_prices) == 0:
                ready = False
                await asyncio.sleep(1)
        exchange_data_ready = ready

    while True:
        stdscr.clear()
        best_cycle_rates, best_profit = get_best_opportunity(arbitrage_cycles, originating_exchange, exchanges_data)
        log_message = f"Last check at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n"
        for ticker_key, best_rate, best_exchange, reversed in best_cycle_rates:
            rate_string = f"{best_rate:.15f}".rstrip("0").rstrip(".")
            log_message += f"{ticker_key} on exchange {best_exchange}: {rate_string}"
            if reversed:
                log_message += f" (reversed from {1/best_rate:.2f})\n"
            else:
                log_message += "\n"
        log_message += f"Best possible profit: {best_profit}\n"
        if best_profit > 1:
            log_message += "\n##############################\n"
            log_message += "##                          ##\n"
            log_message += "##    OPPORTUNITY FOUND!    ##\n"
            log_message += "##                          ##\n"
            log_message += "##############################\n\n"
        else:
            log_message += "\nNo arbitrage opportunities found (yet).\n\n"
        log_message += "Checking for arbitrage opportunities..."
        # Print the log message to the curses window
        stdscr.addstr(1, 0, log_message)
        stdscr.refresh()
        
        await asyncio.sleep(check_period)



if __name__ == '__main__':
    curses.wrapper(lambda stdscr: asyncio.run(main(stdscr)))
