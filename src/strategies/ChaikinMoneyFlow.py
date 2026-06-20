import pandas as pd
from src.strategies import Strategy
from ta.volume import ChaikinMoneyFlowIndicator
import logging

# Configure logging format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CMFStrategy(Strategy.Strategy):
    def __init__(self, window: int = 20, buy_threshold: float = 0.1, sell_threshold: float = -0.1):
        # Requires at least the window size to calculate the volume accumulations
        super().__init__(name="Chaikin Money Flow", min_bars_required=window, is_continuous=False)
        self.window = window
        self.buy_threshold = buy_threshold  # e.g., 0.10 means strong institutional buying
        self.sell_threshold = sell_threshold  # e.g., -0.10 means strong institutional selling

        logger.info(
            f"CMF Strategy initialized: window={self.window}, buy_threshold={self.buy_threshold}, sell_threshold={self.sell_threshold}"
        )

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds
        logger.debug(f"Checking data length. Available bars: {len(df)}, Required: {self.min_bars_required}")
        assert len(df) >= self.min_bars_required, \
            f'This strategy needs at least {self.min_bars_required} candles to run.'

        # Initialize CMF Indicator (requires high, low, close, and volume columns)
        cmf_ind = ChaikinMoneyFlowIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            volume=df['tick_volume'],
            window=self.window
        )

        # Extract current and previous values to capture crossing momentum
        cmf_series = cmf_ind.chaikin_money_flow()
        prev_cmf = cmf_series.iloc[-2]
        curr_cmf = cmf_series.iloc[-1]

        logger.info(
            f"Current CMF: {curr_cmf:.4f} | Previous CMF: {prev_cmf:.4f} | Position: {current_position}"
        )

        # State: No active position -> Look for institutional momentum breaks
        if current_position == 0:
            # Bullish: CMF crosses ABOVE the buy threshold (accumulation confirmation)
            if prev_cmf <= self.buy_threshold and curr_cmf > self.buy_threshold:
                logger.info(f"Signal Generated: 1 (Institutional Accumulation: {curr_cmf:.4f} > {self.buy_threshold})")
                return 1

            # Bearish: CMF crosses BELOW the sell threshold (distribution confirmation)
            elif prev_cmf >= self.sell_threshold and curr_cmf < self.sell_threshold:
                logger.info(
                    f"Signal Generated: -1 (Institutional Distribution: {curr_cmf:.4f} < {self.sell_threshold})")
                return -1

            return 0

        # State: Currently Long -> Exit if buying volume dies out and flips negative
        elif current_position == 1:
            if curr_cmf < 0.0:
                logger.info(f"Signal Generated: 2 (Exit Long: Capital flow turned negative {curr_cmf:.4f})")
                return 2
            return 0

        # State: Currently Short -> Exit if selling volume dies out and flips positive
        else:
            if curr_cmf > 0.0:
                logger.info(f"Signal Generated: 2 (Exit Short: Capital flow turned positive {curr_cmf:.4f})")
                return 2
            return 0