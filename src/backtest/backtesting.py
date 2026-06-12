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

    back_test_results = {'symbol': symbol, 'time frame': time_frame, 'Financial data': pd.DataFrame()}

    df = data_loader(symbol, time_frame)

    back_test_results['Financial data'] = df

    current_position = 0

    long_price = []
    short_price = []

    for i in tqdm(range(len(df)-strategy.min_bars_required)):
        df_sliced = df.iloc[i:i+strategy.min_bars_required]

        current_close = df_sliced['close'].iloc[-1]
        dt = pd.to_datetime(
            df_sliced['date'].iloc[-1] + " " + df_sliced['time'].iloc[-1],
            format="%Y.%m.%d %H:%M:%S"
        )

        signal = strategy.calculate_signal(df_sliced)

        is_continuous_reversal_long = strategy.is_continuous and signal == -1 and current_position == 1
        is_continuous_reversal_short = strategy.is_continuous and signal == 1 and current_position == -1

        if signal == 2 or is_continuous_reversal_long or is_continuous_reversal_short:
            if current_position == 1 and len(long_price) > 0:
                long_price[-1][-1] = [current_close, dt]  # Close the long trade
                current_position = 0  # Revert state to Flat
            elif current_position == -1 and len(short_price) > 0:
                short_price[-1][-1] = [current_close, dt]  # Close the short trade
                current_position = 0  # Revert state to Flat

            # 4. Handle Entries: Execute when a signal triggers and we aren't already sitting in that position
        if signal == 1 and current_position != 1:
            long_price.append([[current_close, dt], None])
            current_position = 1

        elif signal == -1 and current_position != -1:
            short_price.append([[current_close, dt], None])
            current_position = -1

    # Cleanup trailing unclosed operations at the absolute end of structural history
    if len(short_price) > 0 and short_price[-1][1] is None:
        short_price = short_price[:-1]
    if len(long_price) > 0 and long_price[-1][1] is None:
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

    back_test_results['Trades data'] = df_trades

    if df_trades.empty:
        return back_test_results

    df_trades = df_trades.sort_values("entry_date").reset_index(drop=True)

    df_trades['price_change'] = df_trades['exit_price'] - df_trades['entry_price']
    df_trades['profit'] = df_trades['price_change'] * df_trades['direction']
    df_trades["cum_profit"] = df_trades["profit"].cumsum()

    sum_profits = sum(df_trades[df_trades['profit'] > 0]['profit'].tolist())
    sum_loss = -sum(df_trades[df_trades['profit'] < 0]['profit'].tolist())
    profit_factor = sum_profits / sum_loss

    back_test_results['profit factor'] = profit_factor
    back_test_results['total income'] = sum_profits

    roi = sum_profits * 10
    back_test_results['roi'] = roi

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
    back_test_results['profit to time chart'] = plt


    # 1. Extract boundary datetimes
    earliest_date = df['datetime'].min()
    latest_trade_date = df_trades['exit_date'].max()

    # 2. Calculate time delta in years
    time_delta = latest_trade_date - earliest_date
    years = time_delta.total_seconds() / (365.25 * 24 * 3600)  # Accurate fractional year calculation

    # 3. Define an initial account balance to ground the compounding math
    initial_balance = 100.0
    ending_balance = initial_balance + sum_profits

    # 4. Handle safety edge cases (e.g., zero years or catastrophic losses)
    if years > 0 and ending_balance > 0:
        cagr = (ending_balance / initial_balance) ** (1 / years) - 1
        cagr_percentage = cagr * 100
        back_test_results['cagr'] = cagr_percentage
        back_test_results['time span'] = years
        back_test_results['back test time start'] = earliest_date
        back_test_results['back test time end'] = latest_trade_date

    return back_test_results

def back_tester_results(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):
    results = back_tester(strategy, symbol, time_frame)
    if results['Trades data'].empty:
        print('Seems this strategy not generated any signals, for accurate inspection, checking logs is highly recommended')
    else:
        print(f'Profit factor: {results['profit factor']}')
        print(f'ROI is: {results['roi']:.1f}%')
        print(f'Backtest Horizon: {results['time span']} years ({results['back test time start']} to {results['back test time end']})')
        print(f"CAGR: {results['cagr']:.2f}%")
        results['profit to time chart'].show()