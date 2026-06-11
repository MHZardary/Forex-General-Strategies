# Todo: Add commenting
# Todo: Error handling
# Todo: logging
# Todo: Define more criterias
# Todo: Calculate CAGR shapre Ratio and sortino ratio together

from src.backtest import backtesting as BT
from src.strategies import MACrossover as MACr

BT.back_tester(MACr.MACrossover())
