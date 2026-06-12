import pandas as pd
from src.indicators import MA
from src.strategies import Strategy

class MACrossover(Strategy.Strategy):
    def __init__(self, short_window: int = 50, long_window: int = 200):
        # The minimum bars needed matches the length of the slow moving average
        super().__init__(name="Moving Average Crossover", min_bars_required=long_window+1, is_continuous=True)
        self.short_window = short_window
        self.long_window = long_window

    def calculate_signal(self, df: pd.DataFrame) -> int:
        assert len(df) >= self.min_bars_required, \
            f'this strategy needs at least {self.min_bars_required} candles to run.'

        if len(df) < self.long_window:
            raise ValueError(f"Not enough data: DataFrame only has {len(df)} rows, but {self.long_window} are required.")

        if self.long_window <= self.short_window:
            raise ValueError(f"Logic error: big_ma ({self.long_window}) must be greater than small_ma ({self.short_window}).")

        # 2. Calculate Moving Averages
        short_ma_series = df['close'].rolling(window=self.short_window).mean()
        long_ma_series = df['close'].rolling(window=self.long_window).mean()


        # Extract the last two values (previous bar and current bar)
        prev_small = short_ma_series.iloc[-2]
        curr_small = short_ma_series.iloc[-1]

        prev_big = long_ma_series.iloc[-2]
        curr_big = long_ma_series.iloc[-1]

        # 3. Determine Signal
        # Golden Cross: Small crosses ABOVE Big
        if prev_small <= prev_big and curr_small > curr_big:
            return 1

        # Death Cross: Small crosses BELOW Big
        elif prev_small >= prev_big and curr_small < curr_big:
            return -1

        return 0
