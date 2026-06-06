import pandas as pd
from src.indicators import MA

def macross(df: pd.DataFrame, small_ma: int = 20, big_ma: int = 200) -> int:
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