import pandas as pd
from src.strategies import Strategy
from ta.trend import MACD as MACDIndicator
import logging

# Configure logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MACD(Strategy.Strategy):
    def __init__(self, window_fast: int = 12, window_slow: int = 26, window_sign: int = 9):
        # The slow window requires 26 bars, plus the signal line needs 9 bars of the MACD line.
        # We ensure safety by setting min_bars to window_slow + window_sign
        min_bars = window_slow + window_sign
        super().__init__(name="MACD", min_bars_required=min_bars, is_continuous=False)

        self.window_fast = window_fast
        self.window_slow = window_slow
        self.window_sign = window_sign

        logger.info(
            f"MACD Strategy initialized: fast={self.window_fast}, slow={self.window_slow}, sign={self.window_sign}"
        )

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds
        logger.debug(f"Checking data length. Available bars: {len(df)}, Required: {self.min_bars_required}")
        assert len(df) >= self.min_bars_required, \
            f'This strategy needs at least {self.min_bars_required} candles to run.'

        # Initialize MACD Indicator
        macd_ind = MACDIndicator(
            close=df['close'],
            window_fast=self.window_fast,
            window_slow=self.window_slow,
            window_sign=self.window_sign
        )

        # Generate vectors for cross-over detection
        macd_series = macd_ind.macd()
        signal_series = macd_ind.macd_signal()

        # Extract current and previous values to detect lines crossing
        prev_macd = macd_series.iloc[-2]
        curr_macd = macd_series.iloc[-1]

        prev_signal = signal_series.iloc[-2]
        curr_signal = signal_series.iloc[-1]

        logger.info(
            f"MACD: {curr_macd:.4f} | Signal: {curr_signal:.4f} | Position: {current_position}"
        )

        # State: No active position -> Look for entries
        if current_position == 0:
            # Bullish Crossover: MACD line crosses ABOVE the Signal line
            if prev_macd <= prev_signal and curr_macd > curr_signal:
                logger.info(f"Signal Generated: 1 (Bullish MACD Crossover: {curr_macd:.4f} > {curr_signal:.4f})")
                return 1

            # Bearish Crossover: MACD line crosses BELOW the Signal line
            elif prev_macd >= prev_signal and curr_macd < curr_signal:
                logger.info(f"Signal Generated: -1 (Bearish MACD Crossover: {curr_macd:.4f} < {curr_signal:.4f})")
                return -1

            return 0

        # State: Currently Long -> Exit when momentum stalls or reverses
        elif current_position == 1:
            # Exit long position if a bearish crossover occurs
            if prev_macd >= prev_signal and curr_macd < curr_signal:
                logger.info("Signal Generated: 2 (Exit Long: Bearish MACD Crossover detected)")
                return 2
            return 0

        # State: Currently Short -> Exit when momentum stalls or reverses
        else:
            # Exit short position if a bullish crossover occurs
            if prev_macd <= prev_signal and curr_macd > curr_signal:
                logger.info("Signal Generated: 2 (Exit Short: Bullish MACD Crossover detected)")
                return 2
            return 0