import pandas as pd
from src.indicators import MA
from src.strategies import Strategy

class MACrossover(Strategy.Strategy):
    def __init__(self, short_window: int = 50, long_window: int = 200):
        # Initialize base Strategy class parameters with window safety requirements
        super().__init__(name="Moving Average Crossover", min_bars_required=long_window+1, is_continuous=True)
        self.short_window = short_window
        self.long_window = long_window

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds required to run the strategy
        assert len(df) >= self.min_bars_required, \
            f'this strategy needs at least {self.min_bars_required} candles to run.'

        # Validate that historical data meets the long window calculation requirements
        if len(df) < self.long_window:
            raise ValueError(f"Not enough data: DataFrame only has {len(df)} rows, but {self.long_window} are required.")

        # Prevent misconfiguration errors between window parameters
        if self.long_window <= self.short_window:
            raise ValueError(f"Logic error: big_ma ({self.long_window}) must be greater than small_ma ({self.short_window}).")

        # Compute historical moving average vectors over the closing price series
        short_ma_series = df['close'].rolling(window=self.short_window).mean()
        long_ma_series = df['close'].rolling(window=self.long_window).mean()

        # Extract crossover validation points using negative relative index positions
        prev_small = short_ma_series.iloc[-2]
        curr_small = short_ma_series.iloc[-1]

        prev_big = long_ma_series.iloc[-2]
        curr_big = long_ma_series.iloc[-1]

        # Evaluate Crossover Events
        # Golden Cross: Fast MA crosses ABOVE Slow MA (Buy Signal)
        if prev_small <= prev_big and curr_small > curr_big:
            return 1

        # Death Cross: Fast MA crosses BELOW Slow MA (Sell Signal)
        elif prev_small >= prev_big and curr_small < curr_big:
            return -1

        # Default fallback state when no intersection occurs
        return 0
