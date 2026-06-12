from src.core import metatrader as MT
import MetaTrader5 as mt5
import time
from src.strategies import Strategy
import pandas as pd

def live(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):

    if not mt5.initialize():
        return 0

    my_dataframe = pd.DataFrame()
    current_balance = MT.get_account_balance()
    trade_scale = int(current_balance / 100)
    last_processed_time = None

    try:
        while len(my_dataframe) < strategy.min_bars_required:
            my_dataframe = MT.update_candle_dataframe(
                my_dataframe, symbol, time_frame, strategy.min_bars_required
            )

        while True:
            my_dataframe = MT.update_candle_dataframe(
                my_dataframe, symbol, time_frame, strategy.min_bars_required
            )

            current_latest_time = my_dataframe['time'].max()
            if last_processed_time is not None and current_latest_time == last_processed_time:
                time.sleep(1)
                continue

            last_processed_time = current_latest_time

            stats = MT.get_positions_summary(symbol)

            if stats["buy_lots"] > 0:
                current_position = 1
            elif stats["sell_lots"] > 0:
                current_position = -1
            else:
                current_position = 0

            # 2. Derive current active state bias (1 = Long, -1 = Short, 0 = Flat)
            if stats["buy_lots"] > 0:
                current_position = 1
            elif stats["sell_lots"] > 0:
                current_position = -1
            else:
                current_position = 0

            # 3. Pass current live position context into calculation
            signal = strategy.calculate_signal(my_dataframe, current_position)

            if signal == 0:
                continue

            is_continuous_reversal_long = strategy.is_continuous and signal == -1 and current_position == 1
            is_continuous_reversal_short = strategy.is_continuous and signal == 1 and current_position == -1

            if signal == 2 or is_continuous_reversal_long or is_continuous_reversal_short:
                print(f"[{current_latest_time}] Execution Event -> Flattening position for {symbol}.")
                MT.close_market_positions(symbol)
                # Refresh our stats matrix since we just flattened exposure
                stats = {"buy_lots": 0.0, "sell_lots": 0.0}
                current_position = 0

            # =========================================================
            # PROCESS BUY / ENTRY LONG SIGNALS
            # =========================================================
            if signal == 1:
                # If we have short exposure remaining somehow, clean it out first
                if stats["sell_lots"] > 0:
                    MT.close_market_positions(symbol)
                    stats["sell_lots"] = 0.0

                # Simple allocation management to reach our target lot size
                if stats["buy_lots"] == 0:
                    print(f"[{current_latest_time}] Execution Event -> Opening new Long trade.")
                    MT.open_market_position(symbol=symbol, order_type="buy", volume=target_volume)
                elif stats["buy_lots"] < target_volume:
                    needed_vol = round(target_volume - stats["buy_lots"], 2)
                    if needed_vol >= 0.01:
                        MT.open_market_position(symbol=symbol, order_type="buy", volume=needed_vol)
                elif stats["buy_lots"] > target_volume:
                    # Optional scale down safety
                    MT.close_market_positions(symbol)
                    MT.open_market_position(symbol=symbol, order_type="buy", volume=target_volume)

            # =========================================================
            # PROCESS SELL / ENTRY SHORT SIGNALS
            # =========================================================
            elif signal == -1:
                # If we have long exposure remaining somehow, clean it out first
                if stats["buy_lots"] > 0:
                    MT.close_market_positions(symbol)
                    stats["buy_lots"] = 0.0

                # Simple allocation management to reach our target lot size
                if stats["sell_lots"] == 0:
                    print(f"[{current_latest_time}] Execution Event -> Opening new Short trade.")
                    MT.open_market_position(symbol=symbol, order_type="sell", volume=target_volume)
                elif stats["sell_lots"] < target_volume:
                    needed_vol = round(target_volume - stats["sell_lots"], 2)
                    if needed_vol >= 0.01:
                        MT.open_market_position(symbol=symbol, order_type="sell", volume=needed_vol)
                elif stats["sell_lots"] > target_volume:
                    # Optional scale down safety
                    MT.close_market_positions(symbol)
                    MT.open_market_position(symbol=symbol, order_type="sell", volume=target_volume)

    except KeyboardInterrupt:
        print("\nStopping live execution script cleanly...")
    finally:
        mt5.shutdown()
    return 1

