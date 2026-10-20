# BTC Agent — Paper-Trading Prototype

## Overview

An **isolated** Bitcoin paper-trading prototype for testing strategy ideas before any real-world deployment.

## Design Principles

- **Public data only:** Uses publicly available BTC/USDT market data (e.g., Binance public API, CoinGecko). No private keys, API secrets, or credentials are required or used.
- **Simulated capital:** Starts with a **$10 virtual balance**. All trades are simulated — no real money changes hands.
- **Strategy — 5/20 SMA crossover:**
  - Fast EMA/SMA period: 5
  - Slow EMA/SMA period: 20
  - Buy signal: fast line crosses above slow line
  - Sell signal: fast line crosses below slow line
- **Fee modeling:** Transaction costs (e.g., 0.1 % per trade) are deducted from the simulated balance to reflect realistic outcomes.
- **No leverage:** Only spot-style trading. No margin, no futures, no borrowed funds.
- **Tests before deployment:** All logic is unit-tested and backtested against historical data before any consideration of live use.
- **Explicitly no real orders or secrets:** This prototype never places live orders and never stores or transmits any secrets or credentials.

## File Structure

```
btc-agent/
├── README.md          ← You are here
├── paper_engine.py    ← Core paper-trading simulation engine
├── sma_strategy.py    ← 5/20 SMA crossover strategy logic
├── fee_model.py       ← Fee calculation module
└── tests/             ← Unit and integration tests
```

## Getting Started

1. Clone the repository.
2. Run the test suite: `pytest btc-agent/tests/`
3. Execute a backtest: `python btc-agent/paper_engine.py`

## Disclaimer

This is a **paper-trading prototype only**. It is intended for research and education. Do not use this code to trade real funds.
