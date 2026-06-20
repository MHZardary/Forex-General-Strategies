import pandas as pd
from src.strategies import Strategy
from ta.volatility import BollingerBands
import logging

# Configure logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BollingerBandsStrategy(Strategy.Strategy):
    def __init__(self, window: int = 20, window_dev: int = 2):
        # Requires at least the window size to calculate the moving average and standard deviation
        super().__init__(name="Bollinger Bands", min_bars_required=window, is_continuous=False)
        self.window = window
        self.window_dev = window_dev

        logger.info(
            f"Bollinger Bands Strategy initialized: window={self.window}, window_dev={self.window_dev}"
        )

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds required to run the strategy
        logger.debug(f"Checking data length. Available bars: {len(df)}, Required: {self.min_bars_required}")
        assert len(df) >= self.min_bars_required, \
            f'This strategy needs at least {self.min_bars_required} candles to run.'

        # Initialize Bollinger Bands Indicator
        indicator_bb = BollingerBands(close=df['close'], window=self.window, window_dev=self.window_dev)

        # Extract current market values
        current_close = df['close'].iloc[-1]
        high_band = indicator_bb.bollinger_hband().iloc[-1]
        low_band = indicator_bb.bollinger_lband().iloc[-1]
        mid_band = indicator_bb.bollinger_mavg().iloc[-1]

        logger.info(
            f"Close: {current_close:.2f} | Upper: {high_band:.2f} | Mid: {mid_band:.2f} | Lower: {low_band:.2f} | Position: {current_position}"
        )

        # State: No active position -> Look for entries
        if current_position == 0:
            # Price breaks below lower band -> Oversold / Long Entry Opportunity
            if current_close < low_band:
                logger.info(f"Signal Generated: 1 (Price {current_close:.2f} broke below Lower Band {low_band:.2f})")
                return 1
            # Price breaks above upper band -> Overbought / Short Entry Opportunity
            elif current_close > high_band:
                logger.info(f"Signal Generated: -1 (Price {current_close:.2f} broke above Upper Band {high_band:.2f})")
                return -1
            else:
                logger.debug("Signal Generated: 0 (Price within bands)")
                return 0

        # State: Currently Long -> Look to exit at the mid-line (mean reversion)
        elif current_position == 1:
            if current_close >= mid_band:
                logger.info(f"Signal Generated: 2 (Exit Long: Price {current_close:.2f} reached/exceeded Mid Band {mid_band:.2f})")
                return 2
            else:
                logger.debug("Signal Generated: 0 (Holding Long position)")
                return 0

        # State: Currently Short -> Look to exit at the mid-line (mean reversion)
        else:
            if current_close <= mid_band:
                logger.info(f"Signal Generated: 2 (Exit Short: Price {current_close:.2f} reached/dropped below Mid Band {mid_band:.2f})")
                return 2
            else:
                logger.debug("Signal Generated: 0 (Holding Short position)")
                return 0