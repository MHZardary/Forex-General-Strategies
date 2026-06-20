import pandas as pd
import numpy as np
from src.strategies import Strategy
import logging

# Configure logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HeikinAshiStrategy(Strategy.Strategy):
    def __init__(self, trend_strength_bars: int = 3):
        # We need a small lookback buffer to calculate historical HA candles sequentially
        super().__init__(name="Heikin-Ashi Trend", min_bars_required=trend_strength_bars + 5, is_continuous=False)
        self.trend_strength_bars = trend_strength_bars

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds
        logger.debug(f"Checking data length. Available bars: {len(df)}, Required: {self.min_bars_required}")
        assert len(df) >= self.min_bars_required, \
            f'This strategy needs at least {self.min_bars_required} candles to run.'

        # Copy dataframe to avoid mutating the original historical data
        ha_df = df.copy()

        # 1. Calculate Heikin-Ashi Close
        ha_df['ha_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4.0

        # 2. Calculate Heikin-Ashi Open sequentially (depends on previous row's open and close)
        ha_open = np.zeros(len(ha_df))
        ha_open[0] = (ha_df['open'].iloc[0] + ha_df['close'].iloc[0]) / 2.0

        for i in range(1, len(ha_df)):
            ha_open[i] = (ha_open[i - 1] + ha_df['ha_close'].iloc[i - 1]) / 2.0

        ha_df['ha_open'] = ha_open

        # 3. Calculate Heikin-Ashi High and Low
        ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
        ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)

        # Slice the last few candles to evaluate structural momentum strength
        recent_ha = ha_df.tail(self.trend_strength_bars)

        # Check if last N bars are completely green (bullish trend)
        is_bullish_trend = all(recent_ha['ha_close'] > recent_ha['ha_open'])
        # Check if last N bars are completely red (bearish trend)
        is_bearish_trend = all(recent_ha['ha_close'] < recent_ha['ha_open'])

        # Read the immediate last candle details for logging
        last_candle = ha_df.iloc[-1]
        logger.info(
            f"HA Open: {last_candle['ha_open']:.2f} | HA Close: {last_candle['ha_close']:.2f} | Position: {current_position}"
        )

        # State: No active position -> Look for strict trend confirmation
        if current_position == 0:
            if is_bullish_trend:
                logger.info(
                    f"Signal Generated: 1 (Confirmed strong Bullish HA structure for {self.trend_strength_bars} bars)")
                return 1
            elif is_bearish_trend:
                logger.info(
                    f"Signal Generated: -1 (Confirmed strong Bearish HA structure for {self.trend_strength_bars} bars)")
                return -1
            return 0

        # State: Currently Long -> Exit the moment a single red reversal candle appears
        elif current_position == 1:
            if last_candle['ha_close'] < last_candle['ha_open']:
                logger.info("Signal Generated: 2 (Exit Long: First bearish HA candle color change detected)")
                return 2
            return 0

        # State: Currently Short -> Exit the moment a single green reversal candle appears
        else:
            if last_candle['ha_close'] > last_candle['ha_open']:
                logger.info("Signal Generated: 2 (Exit Short: First bullish HA candle color change detected)")
                return 2
            return 0