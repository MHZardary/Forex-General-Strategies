from src.backtest import backtesting as BT
from src.strategies import MACrossover as MACr

BT.back_tester_results(MACr.MACrossover())
