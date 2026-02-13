# triarb-detector

A Python-based real-time tool for detecting triangular arbitrage opportunities across multiple cryptocurrency exchanges. It streams live order book data via WebSockets, constructs a directed currency graph, and continuously evaluates arbitrage cycles to find profitable trading paths.

## How It Works

1. **Bootstrap** — Fetches all available trading pairs from each exchange using [ccxt](https://github.com/ccxt/ccxt) REST APIs.
2. **Graph construction** — Builds a directed graph ([NetworkX](https://networkx.org/)) where currencies are nodes and trading pairs are edges.
3. **Cycle detection** — Finds all simple cycles (3–5 hops) originating from the base currency (USDT).
4. **Live price streaming** — Connects to each exchange's WebSocket feed to receive real-time bid/ask prices.
5. **Opportunity evaluation** — Every 100ms, evaluates all candidate cycles by multiplying the best available rates across exchanges, accounting for transaction fees. A product > 1.0 indicates a profitable opportunity.
6. **Terminal display** — Renders results in a `curses`-based terminal UI with live updates.

## Architecture

```
main() [async, curses wrapper]
├── Bootstrap (ccxt REST) → fetch all tickers per exchange
├── Build directed graph from all trading pairs
├── Detect arbitrage cycles starting from USDT
│
├── Concurrent WebSocket tasks:
│   ├── KuCoin         (level2 order book updates)
│   ├── Binance US     (@depth5 streams)
│   ├── Coinbase       (ticker channel)
│   └── Crypto.com     (Kraken WS feed)
│
└── Main loop (100ms interval):
    ├── Evaluate best opportunity across all cycles
    └── Render to terminal
```

All exchange adapters inherit from `ExchangeData`, which provides shared `symbol_prices` storage and bid/ask accessors.

## Supported Exchanges

| Exchange          | Data Source      | Notes                                |
| ----------------- | ---------------- | ------------------------------------ |
| KuCoin            | WebSocket (dynamic token) | Batches subscriptions in groups of 98 |
| Binance US        | WebSocket        | Combined depth stream                |
| Coinbase Exchange  | WebSocket        | Ticker channel subscription          |
| Crypto.com        | WebSocket (Kraken) | Currently connects to Kraken's WS endpoint |

## Project Structure

```
src/
├── triarb.py                  # Main entry point
├── Pipfile                    # Dependencies (Pipenv)
├── Pipfile.lock
└── utils/
    ├── ccxt.py                # Exchange bootstrapping via ccxt
    ├── constants.py           # Fiat currency exclusion list
    ├── graph.py               # Graph structures & cycle rotation
    └── exchanges/
        ├── exchange.py        # Base ExchangeData class
        ├── binanceus.py       # Binance US adapter
        ├── coinbaseexchange.py# Coinbase Exchange adapter
        ├── cryptocom.py       # Crypto.com adapter
        └── kucoin.py          # KuCoin adapter
```

## Prerequisites

- Python 3.10
- [Pipenv](https://pipenv.pypa.io/)

## Setup & Usage

```bash
cd src
pipenv install
pipenv run python triarb.py
```

No API keys are required — all exchanges are accessed via public WebSocket feeds.

## Configuration

Parameters are defined in `triarb.py`:

| Parameter              | Default          | Description                                      |
| ---------------------- | ---------------- | ------------------------------------------------ |
| `check_period`         | `0.1` s          | Evaluation interval                              |
| `originating_exchange` | `kucoin`         | Exchange where cycles start/end                  |
| `other_exchanges`      | `coinbaseexchange`, `binanceus` | Additional exchanges for intermediate hops |
| `base_currency`        | `USDT`           | All cycles originate from this currency          |
| `min_cycle`            | `3`              | Minimum hops in a cycle                          |
| `max_cycle`            | `5`              | Maximum hops in a cycle                          |
| `transaction_fee`      | `0.57%`          | Fee applied per hop in profit calculation        |

## Key Dependencies

| Package           | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `ccxt`            | REST API bootstrap for exchange tickers    |
| `websockets`      | Live WebSocket price streaming             |
| `networkx`        | Directed graph & cycle detection           |
| `octobot-commons` | Symbol dataclass for ticker representation |
| `requests`        | HTTP calls (KuCoin token retrieval)        |
