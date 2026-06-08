import pandas as pd
from src.strategies import MACrossover as MAC
from tqdm import tqdm
import matplotlib.pyplot as plt

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

    for i in tqdm(range(len(df)-big_ma-1)):
        df_sliced = df.iloc[i:i+big_ma+1]
        signal = MAC.macross(df_sliced, small_ma, big_ma)
        if signal == 1:
            dt = pd.to_datetime(
                df_sliced['Date'].iloc[-1] + " " + df_sliced['Time'].iloc[-1],
                format="%Y.%m.%d %H:%M:%S"
            )
            if last_signal != 1:
                long_price.append([[df_sliced['Close'].iloc[-1], dt], None])
            if last_signal==-1:
                short_price[-1][-1]=[df_sliced['Close'].iloc[-1], dt]

            last_signal = signal

        if signal == -1:
            dt = pd.to_datetime(
                df_sliced['Date'].iloc[-1] + " " + df_sliced['Time'].iloc[-1],
                format="%Y.%m.%d %H:%M:%S"
            )
            if last_signal != -1:
                short_price.append([[df_sliced['Close'].iloc[-1], dt], None])
            if last_signal == 1:
                long_price[-1][-1] = [df_sliced['Close'].iloc[-1], dt]

            last_signal = signal
    while short_price[-1][1] is None:
        short_price = short_price[:-1]
    while long_price[-1][1] is None:
        long_price = long_price[:-1]


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
        total_income += (pair[0][0]-pair[1][0])

    for pair in long_price:
        total_income += (pair[1][0]-pair[0][0])

    trades = []

    # Long trades
    for trade in long_price:
        entry, exit_l = trade
        trades.append({
            "entry_date": entry[1],
            "entry_price": entry[0],
            "exit_date": exit_l[1],
            "exit_price": exit_l[0],
            "direction": 1
        })

    # Short trades
    for trade in short_price:
        entry, exit_l = trade
        trades.append({
            "entry_date": entry[1],
            "entry_price": entry[0],
            "exit_date": exit_l[1],
            "exit_price": exit_l[0],
            "direction": -1
        })

    # Create and sort DataFrame
    df_trades = pd.DataFrame(trades)
    df_trades = df_trades.sort_values("entry_date").reset_index(drop=True)

    df_trades['price_change'] = df_trades['exit_price'] - df_trades['entry_price']
    df_trades['profit'] = df_trades['price_change'] * df_trades['direction']
    df_trades["cum_profit"] = df_trades["profit"].cumsum()

    sum_profits = sum(df_trades[df_trades['profit']>0]['profit'].tolist())
    sum_loss = -sum(df_trades[df_trades['profit'] < 0]['profit'].tolist())
    profit_factor = sum_profits/sum_loss
    print(f'Profit factor: {profit_factor}')

    roi = total_income*10
    print(f'ROI is: {roi:.1f}%')

    plt.figure(figsize=(12, 6))

    # Profit per trade
    plt.plot(
        df_trades["exit_date"],
        df_trades["profit"],
        label="Trade Profit",
        linewidth=1.5,
    )

    # Accumulated profit
    plt.plot(
        df_trades["exit_date"],
        df_trades["cum_profit"],
        label="Accumulated Profit",
        linewidth=2,
    )

    plt.xlabel("Date")
    plt.ylabel("Profit")
    plt.title("Trading Performance")
    plt.legend()

    # Rotate date labels for readability
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.show()

    return total_income
