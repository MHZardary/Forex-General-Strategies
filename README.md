# Forex General Strategies

A Python-based research framework for developing, visualizing, and testing Forex trading strategies.

## Overview

This project aims to provide a clean and extensible environment for experimenting with technical indicators and trading strategies on historical Forex data.

Current features include:

* Candlestick chart visualization
* Simple Moving Averages (SMA)
* Relative Strength Index (RSI)
* Multi-indicator plotting
* Historical OHLC data processing
* Modular architecture for future strategy development

The long-term objective is to build a lightweight research and backtesting framework for algorithmic Forex trading.

---

## Features

### Data Processing

* Import historical CSV data.
* Clean and standardize OHLC datasets.
* Automatic datetime handling.

### Technical Indicators

Currently implemented:

* Simple Moving Average (SMA)
* Relative Strength Index (RSI)

Planned:

* EMA
* MACD
* Bollinger Bands
* ATR
* Stochastic Oscillator
* Singular Spectrum Analysis (SSA)

### Charting

* Candlestick charts.
* Multiple SMA overlays.
* RSI panels.
* Dark theme visualization.
* Configurable display window.

### Strategy Research

Planned support for:

* Trend-following strategies
* Mean reversion strategies
* Breakout strategies
* Multi-timeframe analysis
* Indicator combinations

---

## Project Structure

```
Forex-General-Strategies/

├── data/
│   └── Historical market data
│
├── src/
│   ├── indicators/
│   ├── strategies/
│   ├── backtest/
│   ├── visualization/
│   └── utils/
│
├── tests/
│
├── main.py
├── requirements.txt
└── README.md
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/MHZardary/Forex-General-Strategies.git
```

Enter the project directory:

```bash
cd Forex-General-Strategies
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Data Format

The project expects OHLC Forex data similar to MetaTrader exports.

Example:

| Date       | Time     | Open    | High    | Low     | Close   |
| ---------- | -------- | ------- | ------- | ------- | ------- |
| 2026.03.02 | 10:37:00 | 1.17030 | 1.17045 | 1.17028 | 1.17029 |

Additional columns such as volume and spread are supported.

---

## Example Usage

Load data:

```python
data = pd.read_csv(...)
```

Calculate indicators:

```python
add_sma(data, 20)
add_sma(data, 200)
add_rsi(data)
```

Visualize:

```python
plot_price_indicators(
    data,
    sma_periods=[20, 200],
    rsi_periods=[14],
    last_n=60
)
```

---

## Roadmap

### Indicators

* [x] SMA
* [x] RSI
* [ ] EMA
* [ ] MACD
* [ ] Bollinger Bands
* [ ] ATR
* [ ] SSA

### Strategy Engine

* [ ] Buy/Sell signal generation
* [ ] Position management
* [ ] Risk management
* [ ] Multiple strategies

### Backtesting

* [ ] Trade simulator
* [ ] Equity curve
* [ ] Drawdown analysis
* [ ] Win rate
* [ ] Profit factor
* [ ] Sharpe ratio

### Visualization

* [x] Candlesticks
* [x] Indicator overlays
* [ ] Buy/Sell markers
* [ ] Trade history
* [ ] Interactive charts

---

## Future Goals

This project is intended to evolve into a modular Forex research framework capable of:

* Strategy development
* Historical backtesting
* Parameter optimization
* Performance evaluation
* Comparative strategy analysis

---

## Contributing

Contributions, ideas, and bug reports are welcome.

Feel free to open an issue or submit a pull request.

---

## Disclaimer

This project is for educational and research purposes only.

Nothing in this repository should be considered financial or investment advice. Trading financial markets involves significant risk, and past performance does not guarantee future results.

---

## License

This project is released under the MIT License.
