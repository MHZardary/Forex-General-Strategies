import pandas as pd
from src.indicators import MA
from src.core import metatrader as MT
import MetaTrader5 as mt5
import time

def macross(df: pd.DataFrame, small_ma: int = 50, big_ma: int = 200) -> int:
    """
    :param df: price data
    :param small_ma: the value of short-term moving average
    :param big_ma: the value of long-term moving average
    :return: signal: +1 for going long and -1 for going short 0 for none
    """
    if len(df) < big_ma:
        raise ValueError(f"Not enough data: DataFrame only has {len(df)} rows, but {big_ma} are required.")

    if big_ma <= small_ma:
        raise ValueError(f"Logic error: big_ma ({big_ma}) must be greater than small_ma ({small_ma}).")

    # 2. Calculate Moving Averages
    # We use .iloc[-2:] to get the last two calculated values for the signal
    MA.add_sma(df, small_ma)
    MA.add_sma(df, big_ma)

    # Get the last two values for both MAs
    # prev = row before last, curr = latest row
    prev_small = df[f'MA_{small_ma}'].iloc[-2]
    curr_small = df[f'MA_{small_ma}'].iloc[-1]
    prev_big = df[f'MA_{big_ma}'].iloc[-2]
    curr_big = df[f'MA_{big_ma}'].iloc[-1]

    # 3. Determine Signal
    # Golden Cross: Small crosses ABOVE Big
    if prev_small <= prev_big and curr_small > curr_big:
        return 1

    # Death Cross: Small crosses BELOW Big
    elif prev_small >= prev_big and curr_small < curr_big:
        return -1

    return 0

def macross_live(SYMBOL: str = "EURUSD", TIMEFRAME = mt5.TIMEFRAME_M1, big_ma: int = 200, small_ma: int = 50):
    """

    :return:
    """
    N = big_ma + 1
    if not mt5.initialize():
        return 0

    my_dataframe = pd.DataFrame()
    current_balance = MT.get_account_balance()
    trade_scale = int(current_balance/100)
    last_processed_time = None

    try:
        while len(my_dataframe)<N:
            my_dataframe = MT.update_candle_dataframe(
                my_dataframe, SYMBOL, TIMEFRAME, N
            )

        while True:
            my_dataframe = MT.update_candle_dataframe(
                my_dataframe, SYMBOL, TIMEFRAME, N
            )
            current_latest_time = my_dataframe['time'].max()
            if last_processed_time is not None and current_latest_time == last_processed_time:
                time.sleep(1)
                continue

            last_processed_time = current_latest_time
            signal = macross(my_dataframe, small_ma, big_ma)
            if signal == 0:
                continue
            elif signal ==1:
                stats = MT.get_positions_summary(SYMBOL)
                if stats["sell_lots"] > 0:
                    MT.close_market_positions(SYMBOL)
                    MT.open_market_position(symbol=SYMBOL, order_type="buy", volume=(trade_scale*0.01))
                if stats["buy_lots"] > trade_scale:
                    MT.close_market_positions(SYMBOL)
                    MT.open_market_position(symbol=SYMBOL, order_type="buy", volume=(trade_scale * 0.01))
                elif stats["buy_lots"] == 0:
                    MT.open_market_position(symbol=SYMBOL, order_type="buy", volume=(trade_scale*0.01))
                elif stats["buy_lots"] < trade_scale:
                    MT.open_market_position(symbol=SYMBOL, order_type="buy", volume=(trade_scale*0.01-stats["buy_lots"]))

            elif signal == -1:
                stats = MT.get_positions_summary(SYMBOL)
                if stats["buy_lots"] > 0:
                    MT.close_market_positions(SYMBOL)
                    MT.open_market_position(symbol=SYMBOL, order_type="sell", volume=(trade_scale*0.01))
                if stats["sell_lots"] > trade_scale:
                    MT.close_market_positions(SYMBOL)
                    MT.open_market_position(symbol=SYMBOL, order_type="sell", volume=(trade_scale*0.01))
                elif stats["sell_lots"] == 0:
                    MT.open_market_position(symbol=SYMBOL, order_type="sell", volume=(trade_scale*0.01))
                elif stats["sell_lots"] < trade_scale:
                    MT.open_market_position(symbol=SYMBOL, order_type="sell", volume=(trade_scale*0.01-stats["sell_lots"]))


    except KeyboardInterrupt:
        print("\nStopping script...")
    finally:
        mt5.shutdown()
    return 1
