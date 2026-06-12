from src.core import LiveTrade as LT
# from src.backtest import backtesting as BT
from src.strategies import RSI

LT.live(RSI.RSI())

# BT.back_tester_results(RSI.RSI())
