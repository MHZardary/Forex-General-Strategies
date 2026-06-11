import pandas as pd
from tqdm import tqdm
from src.strategies import Strategy
import matplotlib.pyplot as plt


def data_loader(symbol: str = 'EURUSD', time_frame: str = '1m')-> pd.DataFrame:
    """
    This function loads the data from the previously saved csv file and returns clean
    pandas data frame called df.
    :param time_frame:
    :param symbol: symbol of
    :return: df: Cleaned dataframe including financial data
    """

    # Generate file name and the path
    file_name = f"{symbol}_{time_frame}.csv"
    path = "data/raw/" + file_name

    # Read the data into raw df
    df = pd.read_csv(path, sep="\t")

    # Extract the names of columns based on the data in csv file
    df.columns = df.columns.str.replace('<', '', regex=False) \
        .str.replace('>', '', regex=False)

    # Change the names of columns to standard notation
    df = df.rename(columns={
        'DATE': 'date',
        'TIME': 'time',
        'OPEN': 'open',
        'HIGH': 'high',
        'LOW': 'low',
        'CLOSE': 'close',
        'TICKVOL': 'tick_volume',
        'VOL': 'volume',
        'SPREAD': 'spread'
    })

    # Create 'Datetime' column for the df
    df['datetime'] = pd.to_datetime(
        df['date'] + ' ' + df['time'],
        format="%Y.%m.%d %H:%M:%S",
    )

    return df

def back_tester(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):

    df = data_loader(symbol, time_frame)
    last_signal = 0
    long_price = []
    short_price = []

    for i in tqdm(range(len(df)-strategy.min_bars_required)):
        df_sliced = df.iloc[i:i+strategy.min_bars_required]
        signal = strategy.calculate_signal(df_sliced)
        if signal == 1:
            dt = pd.to_datetime(
                df_sliced['date'].iloc[-1] + " " + df_sliced['time'].iloc[-1],
                format="%Y.%m.%d %H:%M:%S"
            )
            if last_signal != 1:
                long_price.append([[df_sliced['close'].iloc[-1], dt], None])
            if last_signal==-1:
                short_price[-1][-1]=[df_sliced['close'].iloc[-1], dt]

            last_signal = signal

        if signal == -1:
            dt = pd.to_datetime(
                df_sliced['date'].iloc[-1] + " " + df_sliced['time'].iloc[-1],
                format="%Y.%m.%d %H:%M:%S"
            )
            if last_signal != -1:
                short_price.append([[df_sliced['close'].iloc[-1], dt], None])
            if last_signal == 1:
                long_price[-1][-1] = [df_sliced['close'].iloc[-1], dt]

            last_signal = signal
    while short_price[-1][1] is None:
        short_price = short_price[:-1]
    while long_price[-1][1] is None:
        long_price = long_price[:-1]

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

    sum_profits = sum(df_trades[df_trades['profit'] > 0]['profit'].tolist())
    sum_loss = -sum(df_trades[df_trades['profit'] < 0]['profit'].tolist())
    profit_factor = sum_profits / sum_loss
    print(f'Profit factor: {profit_factor}')

    total_income = df_trades['profit'].sum()
    roi = total_income * 10
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

    # ==========================================
    # CAGR PERFORMANCE METRICS
    # ==========================================

    # 1. Extract boundary datetimes
    earliest_date = df['datetime'].min()
    latest_trade_date = df_trades['exit_date'].max()

    # 2. Calculate time delta in years
    time_delta = latest_trade_date - earliest_date
    years = time_delta.total_seconds() / (365.25 * 24 * 3600)  # Accurate fractional year calculation

    # 3. Define an initial account balance to ground the compounding math
    initial_balance = 100.0
    ending_balance = initial_balance + total_income

    # 4. Handle safety edge cases (e.g., zero years or catastrophic losses)
    if years > 0 and ending_balance > 0:
        cagr = (ending_balance / initial_balance) ** (1 / years) - 1
        cagr_percentage = cagr * 100
        print(
            f"Backtest Horizon: {years:.2f} years ({earliest_date.strftime('%Y-%m-%d')} to {latest_trade_date.strftime('%Y-%m-%d')})")
        print(f"CAGR: {cagr_percentage:.2f}%")
    else:
        print("CAGR: Cannot be calculated (Time horizon too short or total loss incurred)")

    return 1