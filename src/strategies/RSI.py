import pandas as pd
from src.strategies import Strategy
from ta.momentum import RSIIndicator
import logging

# Configure logging format (if not already configured in your main script)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RSI(Strategy.Strategy):
    def __init__(self, window: int = 14, lower: int = 30, mid_lower = 40, mid_higher: int = 60, higher: int = 70):
        # Initialize base Strategy class parameters with window safety requirements
        super().__init__(name="Moving Average Crossover", min_bars_required=window+1, is_continuous=False)
        self.window = window
        self.lower = lower
        self.mid_lower = mid_lower
        self.mid_higher = mid_higher
        self.higher = higher

        logger.info(
            f"RSI Strategy initialized: window={self.window}, lower={self.lower}, "
            f"mid_lower={self.mid_lower}, mid_higher={self.mid_higher}, higher={self.higher}"
        )

    def calculate_signal(self, df: pd.DataFrame, current_position: int = 0) -> int:
        # Enforce minimum candle history thresholds required to run the strategy
        logger.debug(f"Checking data length. Available bars: {len(df)}, Required: {self.min_bars_required}")
        assert len(df) >= self.min_bars_required, \
            f'this strategy needs at least {self.min_bars_required} candles to run.'

        rsi_indicator = RSIIndicator(close=df['close'], window=self.window)
        rsi_value = rsi_indicator.rsi().iloc[-1]

        logger.info(f"Calculated Current RSI Value: {rsi_value:.2f} | Current Position: {current_position}")

        if current_position==0:
            if rsi_value>self.higher:
                logger.info(f"Signal Generated: -1 (Overbought condition met: {rsi_value:.2f} > {self.higher})")
                return -1
            elif rsi_value<self.lower:
                logger.info(f"Signal Generated: 1 (Oversold condition met: {rsi_value:.2f} < {self.lower})")
                return 1
            else:
                logger.debug("Signal Generated: 0 (RSI in neutral zone)")
                return 0

        elif current_position==1:
            if rsi_value>self.mid_lower:
                logger.info(f"Signal Generated: 2 (Exit Long condition met: {rsi_value:.2f} > {self.mid_lower})")
                return 2
            else:
                logger.debug("Signal Generated: 0 (Holding Long position)")
                return 0

        else:
            if rsi_value<self.mid_higher:
                logger.info(f"Signal Generated: 2 (Exit Short condition met: {rsi_value:.2f} < {self.mid_higher})")
                return 2
            else:
                logger.debug("Signal Generated: 0 (Holding Short position)")
                return 0