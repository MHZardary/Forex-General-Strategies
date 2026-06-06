import pandas as pd
from src.strategies import MACrossover as MAC

def macrossover_btest(symbol: str = 'EURUSD', time_frame: str = 'M1', big_ma: int = 200, small_ma: int = 50):
    file_name = f"{symbol}_{time_frame}.csv"
    path = "data/raw/" + file_name
    df = pd.read_csv(path, sep="\t")


    df.columns = df.columns.str.replace('<', '', regex=False)\
                       .str.replace('>', '', regex=False)

    df = df.rename(columns={
        'DATE': 'Date',
        'TIME': 'Time',
        'OPEN': 'Open',
        'HIGH': 'High',
        'LOW': 'Low',
        'CLOSE': 'Close',
        'TICKVOL': 'TickVolume',
        'VOL': 'Volume',
        'SPREAD': 'Spread'
    })

    long_price = []
    short_price = []
    last_signal = 0

    for i in range(len(df)-big_ma-1):
        df_sliced = df.iloc[i:i+big_ma+1]
        signal = MAC.macross(df_sliced, small_ma, big_ma)
        if signal == 1:
            long_price.append([df_sliced['Close'].iloc[-1], 0])
            if last_signal==-1:
                short_price[-1][-1]=df_sliced['Close']

        if signal == -1:
            short_price.append([df_sliced['Close'].iloc[-1], 0])
            if last_signal == 1:
                long_price[-1][-1] = df_sliced['Close']


    return [short_price, long_price]

def macrossover_btest_analysis(symbol: str = 'EURUSD', time_frame: str = 'M1', big_ma: int = 200, small_ma: int = 50):
    """
    :param symbol:
    :param time_frame:
    :param big_ma:
    :param small_ma:
    :return:
    """
    short_price, long_price = macrossover_btest(symbol, time_frame, big_ma, small_ma)
    total_income = 0
    for pair in short_price:
        total_income += (pair[0]-pair[1])

    for pair in long_price:
        total_income += (pair[1]-pair[0])

    return total_income

