import pandas as pd
from src.strategies import Strategy
from ta.momentum import RSIIndicator

class RSI(Strategy.Strategy):
    def __init__(self, window: int = 14):
        # Initialize base Strategy class parameters with window safety requirements
        super().__init__(name="Moving Average Crossover", min_bars_required=window+1, is_continuous=False)
        self.window = window

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds required to run the strategy
        assert len(df) >= self.min_bars_required, \
            f'this strategy needs at least {self.min_bars_required} candles to run.'

        rsi_indicator = RSIIndicator(close=df['close'], window=self.window)
        rsi_value = rsi_indicator.rsi().iloc[-1]

        if current_position==0:
            if rsi_value>70:
                return -1
            elif rsi_value<30:
                return 1
            else:
                return 0

        elif current_position==1:
            if rsi_value>40:
                return 2
            else:
                return 0

        else:
            if rsi_value<60:
                return 2
            else:
                return 0