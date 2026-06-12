# Todo: Add commenting
# Todo: Error handling
# Todo: logging
# Todo: Define more criterias
# Todo: Calculate sortino ratio

from src.backtest import backtesting as BT
from src.strategies import MACrossover as MACr

BT.back_tester_results(MACr.MACrossover())
