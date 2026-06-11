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
            signal = strategy.calculate_signal(my_dataframe)
            if signal == 0:
                continue
            elif signal == 1:
                stats = MT.get_positions_summary(symbol)
                if stats["sell_lots"] > 0:
                    MT.close_market_positions(symbol)
                    MT.open_market_position(symbol=symbol, order_type="buy", volume=(trade_scale * 0.01))
                if stats["buy_lots"] > trade_scale:
                    MT.close_market_positions(symbol)
                    MT.open_market_position(symbol=symbol, order_type="buy", volume=(trade_scale * 0.01))
                elif stats["buy_lots"] == 0:
                    MT.open_market_position(symbol=symbol, order_type="buy", volume=(trade_scale * 0.01))
                elif stats["buy_lots"] < trade_scale:
                    MT.open_market_position(symbol=symbol, order_type="buy",
                                            volume=(trade_scale * 0.01 - stats["buy_lots"]))

            elif signal == -1:
                stats = MT.get_positions_summary(symbol)
                if stats["buy_lots"] > 0:
                    MT.close_market_positions(symbol)
                    MT.open_market_position(symbol=symbol, order_type="sell", volume=(trade_scale * 0.01))
                if stats["sell_lots"] > trade_scale:
                    MT.close_market_positions(SYMBOL)
                    MT.open_market_position(symbol=symbol, order_type="sell", volume=(trade_scale * 0.01))
                elif stats["sell_lots"] == 0:
                    MT.open_market_position(symbol=symbol, order_type="sell", volume=(trade_scale * 0.01))
                elif stats["sell_lots"] < trade_scale:
                    MT.open_market_position(symbol=symbol, order_type="sell",
                                            volume=(trade_scale * 0.01 - stats["sell_lots"]))


    except KeyboardInterrupt:
        print("\nStopping script...")
    finally:
        mt5.shutdown()
    return 1