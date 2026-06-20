from src.core import LiveTrade as LT
from src.backtest import backtesting as BT
from src.strategies import HeikinAshi

# LT.live(RSI.RSI())

BT.back_tester_results(HeikinAshi.HeikinAshiStrategy(), time_frame='1m')
