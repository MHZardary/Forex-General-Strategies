from src.core import metatrader as MT
import MetaTrader5 as mt5
import time
from src.strategies import Strategy
import pandas as pd

def live(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):
    """
        Executes live trading operations by polling MetaTrader 5 for candle data
        and dispatching orders based on real-time strategy calculations.

        Parameters:
        -----------
        strategy : Strategy.Strategy
            An instance of the trading strategy logic.
        symbol : str, optional
            The financial asset ticker to trade (default is 'EURUSD').
        time_frame : str, optional
            The candle timeframe string interval (default is '1m').

        Returns:
        --------
        int
            Returns 1 on a clean keyboard exit, or 0 if initialization fails.
    """
    # Connect to the MetaTrader 5 terminal application
    if not mt5.initialize():
        print("[Critical] Failed to initialize MT5 terminal on startup.")
        return 0

    # Calculate initial position sizing based on account equity rules
    my_dataframe = pd.DataFrame()
    last_processed_time = None
    warmup_attempts = 0
    max_warmup_attempts = 30

    try:
        # Warm up historical dataframe buffer to meet minimum strategy requirements
        while len(my_dataframe) < strategy.min_bars_required:
            returned_data = MT.update_candle_dataframe(
                my_dataframe, symbol, time_frame, strategy.min_bars_required
            )

            # Guard against internal database ingestion exceptions or connection loss
            if isinstance(returned_data, pd.DataFrame) and not returned_data.empty:
                my_dataframe = returned_data
            else:
                warmup_attempts += 1
                print(f"[Warning] Warmup data poll failed ({warmup_attempts}/{max_warmup_attempts}). Retrying...")
                if warmup_attempts >= max_warmup_attempts:
                    print("[Error] Maximum historical warmup limits exhausted. Terminating core loop safely.")
                    return 0
            time.sleep(1)

        print(f"Warmup successful. History buffer holds {len(my_dataframe)} candles. Entering live trading loop...")

        # Core real-time execution loop
        while True:
            # Check application link visibility and force re-initialization if dropped
            if not mt5.terminal_info() or not mt5.initialize():
                print("[Warning] MetaTrader 5 link down. Attempting dynamic link recovery...")
                time.sleep(5)
                continue

            # Dynamically recalculate target lot volume using live balance snapshots
            current_balance = MT.get_account_balance()
            if current_balance is None:
                print("[Warning] Could not extract live account balance. Skipping calculation pass.")
                time.sleep(2)
                continue
            target_volume = round(max(0.01, float(int(current_balance / 100)) * 0.01), 2)

            # Pull the latest bar metrics from the market stream
            returned_data = MT.update_candle_dataframe(
                my_dataframe, symbol, time_frame, strategy.min_bars_required
            )

            # 🌟 DEFENSIVE GUARD 2: Protect the history buffer variable from being corrupted by integer error values
            if isinstance(returned_data, pd.DataFrame) and not returned_data.empty:
                my_dataframe = returned_data
            else:
                print(f"[Warning] Failed to fetch live data update tick for {symbol}. Postponing calculation step.")
                time.sleep(2)
                continue

            # Time-gating: Skip loop iterations unless a new candle bar has officially arrived
            current_latest_time = my_dataframe['time'].max()
            if pd.isna(current_latest_time):
                print("[Warning] Extracted invalid timestamp from data engine. Skipping iteration.")
                time.sleep(1)
                continue

            if last_processed_time is not None and current_latest_time == last_processed_time:
                time.sleep(1)
                continue

            # Update the candle lock and sync current open positions
            last_processed_time = current_latest_time
            stats = MT.get_positions_summary(symbol)

            # Classify current direction state: 1 = Long, -1 = Short, 0 = Flat
            if stats.get("buy_lots", 0.0) > 0:
                current_position = 1
            elif stats.get("sell_lots", 0.0) > 0:
                current_position = -1
            else:
                current_position = 0

            # Calculate trading signals based on updated historical data and direction state
            signal = strategy.calculate_signal(my_dataframe, current_position)

            if signal == 0:
                time.sleep(1)
                continue

            # Handle explicit flatten instructions (Signal Code: 2)
            if signal == 2:
                print(f"[{current_latest_time}] Execution Event -> Flattening position for {symbol}.")
                MT.close_market_positions(symbol)
                stats = {"buy_lots": 0.0, "sell_lots": 0.0}
                current_position = 0
                time.sleep(1)
                continue

            # PROCESS BUY / ENTRY LONG SIGNALS
            if signal == 1:
                # Continuous Reversal: Clean up conflicting short exposure first
                if stats.get("sell_lots", 0.0) > 0:
                    MT.close_market_positions(symbol, side_to_close="sell")
                    stats["sell_lots"] = 0.0

                    # Allocation Management: Route entry, scale-up, or scale-down orders
                    if stats.get("buy_lots", 0.0) == 0:
                        print(f"[{current_latest_time}] Execution Event -> Opening new Long trade.")
                        MT.open_market_position(symbol=symbol, order_type="buy", volume=target_volume)
                    elif stats["buy_lots"] < target_volume:
                        needed_vol = round(target_volume - stats["buy_lots"], 2)
                        if needed_vol >= 0.01:
                            MT.open_market_position(symbol=symbol, order_type="buy", volume=needed_vol)
                    elif stats["buy_lots"] > target_volume:
                        print(f"[{current_latest_time}] Portfolio Adjustment -> Downscaling long position exposure.")
                        MT.close_market_positions(symbol, side_to_close="buy")
                        time.sleep(0.5)
                        MT.open_market_position(symbol=symbol, order_type="buy", volume=target_volume)

            # PROCESS SELL / ENTRY SHORT SIGNALS
            elif signal == -1:
                # Continuous Reversal: Clean up conflicting long exposure first
                if stats.get("buy_lots", 0.0) > 0:
                    MT.close_market_positions(symbol, side_to_close="buy")
                    stats["buy_lots"] = 0.0

                    # Allocation Management: Route entry, scale-up, or scale-down orders
                    if stats.get("sell_lots", 0.0) == 0:
                        print(f"[{current_latest_time}] Execution Event -> Opening new Short trade.")
                        MT.open_market_position(symbol=symbol, order_type="sell", volume=target_volume)
                    elif stats["sell_lots"] < target_volume:
                        needed_vol = round(target_volume - stats["sell_lots"], 2)
                        if needed_vol >= 0.01:
                            MT.open_market_position(symbol=symbol, order_type="sell", volume=needed_vol)
                    elif stats["sell_lots"] > target_volume:
                        print(f"[{current_latest_time}] Portfolio Adjustment -> Downscaling short position exposure.")
                        MT.close_market_positions(symbol, side_to_close="sell")
                        time.sleep(0.5)
                        MT.open_market_position(symbol=symbol, order_type="sell", volume=target_volume)

                time.sleep(1)  # General loop breathing space to keep connection thread stable

    except KeyboardInterrupt:
        print("\nStopping live execution script cleanly via user command...")
    except Exception as e:
        print(f"\n[Unexpected Core Failure] An unhandled exception forced loop crash: {str(e)}")
    finally:
        # Secure terminal disconnection cleanup
        print("Releasing terminal interface resources...")
        mt5.shutdown()
    return 1

