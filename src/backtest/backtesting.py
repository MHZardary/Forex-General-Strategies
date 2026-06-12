import numpy as np
import pandas as pd
from tqdm import tqdm
from src.strategies import Strategy
import matplotlib.pyplot as plt


def data_loader(symbol: str = 'EURUSD', time_frame: str = '1m')-> pd.DataFrame:
    """
    Loads, cleans, and standardizes raw financial historical CSV data.

    Parameters:
    -----------
    symbol : str, optional
        The financial ticker asset symbol (default is 'EURUSD').
    time_frame : str, optional
        The candlestick timeline bar interval length (default is '1m').

    Returns:
    --------
    pd.DataFrame
        Cleaned and normalized financial dataframe containing standard lowercase
        ohlcv headers and a parsed datetime index column.
    """
    file_name = f"{symbol}_{time_frame}.csv"
    path = "data/raw/" + file_name

    # Import MT5 exported data using standard tab-separated formatting
    df = pd.read_csv(path, sep="\t")

    # Clean header metadata brackets
    df.columns = df.columns.str.replace('<', '', regex=False) \
        .str.replace('>', '', regex=False)

    # Map raw headers to lowercase standard notation
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

    # Combine string date components into a single datetime column
    df['datetime'] = pd.to_datetime(
        df['date'] + ' ' + df['time'],
        format="%Y.%m.%d %H:%M:%S",
    )

    return df

def back_tester(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):
    """
        Simulates trading historical performance over historical time-series datasets.

        Parameters:
        -----------
        strategy : Strategy.Strategy
            An instance of the trading strategy logic defining min_bars_required and calculate_signal.
        symbol : str, optional
            The financial ticker asset symbol (default is 'EURUSD').
        time_frame : str, optional
            The candlestick timeline bar interval length (default is '1m').

        Returns:
        --------
        dict
            A summary dictionary containing evaluation statistics (ROI, CAGR, Sharpe, Sortino ratios),
            raw data logs, and performance visualization figures.
        """

    back_test_results = {'symbol': symbol, 'time frame': time_frame, 'Financial data': pd.DataFrame()}

    # Ingest full historical series
    df = data_loader(symbol, time_frame)
    back_test_results['Financial data'] = df

    current_position = 0
    long_price = []
    short_price = []

    # Historical chronological simulation window iteration loop
    for i in tqdm(range(len(df)-strategy.min_bars_required)):

        # Create a rolling historical snapshot slice matching the strategy buffer requirement
        df_sliced = df.iloc[i:i+strategy.min_bars_required]

        current_close = df_sliced['close'].iloc[-1]
        dt = pd.to_datetime(
            df_sliced['date'].iloc[-1] + " " + df_sliced['time'].iloc[-1],
            format="%Y.%m.%d %H:%M:%S"
        )

        signal = strategy.calculate_signal(df_sliced, current_position)

        # Long state execution management logic
        if current_position == 1:
            if signal == 2 or signal == -1:
                # Close out open active long position array row
                if len(long_price) > 0:
                    long_price[-1][-1] = [current_close, dt]
                current_position = 0

                # Continuous Reversal: Instantly enter opposite short asset state
                if strategy.is_continuous and signal == -1:
                    short_price.append([[current_close, dt], None])
                    current_position = -1

        # Short state execution management logic
        elif current_position == -1:
            if signal == 2 or signal == 1:
                # Close out open active short position array row
                if len(short_price) > 0:
                    short_price[-1][-1] = [current_close, dt]
                    current_position = 0

                # Continuous Reversal: Instantly enter opposite long asset state
                if strategy.is_continuous and signal == 1:
                    long_price.append([[current_close, dt], None])
                    current_position = 1

            # Flat structural execution condition rules
        else:
            if signal == 1:
                long_price.append([[current_close, dt], None])
                current_position = 1
            elif signal == -1:
                short_price.append([[current_close, dt], None])
                current_position = -1

    # Clean up unclosed trailing positions at the terminal edge of the dataset
    if len(short_price) > 0 and short_price[-1][1] is None:
        short_price = short_price[:-1]
    if len(long_price) > 0 and long_price[-1][1] is None:
        long_price = long_price[:-1]


    trades = []

    # Parse short position arrays into a structured trade logger ledger
    for trade in long_price:
        entry, exit_l = trade
        trades.append({
            "entry_date": entry[1],
            "entry_price": entry[0],
            "exit_date": exit_l[1],
            "exit_price": exit_l[0],
            "direction": 1
        })

    # Parse short position arrays into a structured trade logger ledger
    for trade in short_price:
        entry, exit_l = trade
        trades.append({
            "entry_date": entry[1],
            "entry_price": entry[0],
            "exit_date": exit_l[1],
            "exit_price": exit_l[0],
            "direction": -1
        })

    df_trades = pd.DataFrame(trades)
    back_test_results['Trades data'] = df_trades

    # Fallback exit condition for dead asset data feeds
    if df_trades.empty:
        return back_test_results

    # Order positions chronologically by execution entry timestamp
    df_trades = df_trades.sort_values("entry_date").reset_index(drop=True)
    initial_balance = 100.0

    # Calculate absolute returns and raw cumulative profit vectors
    df_trades['price_change'] = df_trades['exit_price'] - df_trades['entry_price']
    df_trades['profit'] = df_trades['price_change'] * df_trades['direction'] * 10
    df_trades["cum_profit"] = df_trades["profit"].cumsum()

    # Performance Matrix: Compute total gross returns vs losses
    sum_profits = sum(df_trades[df_trades['profit'] > 0]['profit'].tolist())
    sum_loss = -sum(df_trades[df_trades['profit'] < 0]['profit'].tolist())
    profit_factor = sum_profits / sum_loss if sum_loss > 0 else float('inf')

    # Store standard financial summary outputs
    back_test_results['profit factor'] = profit_factor
    back_test_results['total income'] = sum_profits - sum_loss
    back_test_results['roi'] = (back_test_results['total income'] / initial_balance) * 100

    # Draw portfolio equity progression charting timelines
    plt.figure(figsize=(12, 6))
    plt.plot(
        df_trades["exit_date"],
        df_trades["profit"],
        label="Trade Profit",
        linewidth=1.5,
    )
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
    plt.xticks(rotation=45)
    plt.tight_layout()
    back_test_results['profit to time chart'] = plt

    # Calculate precise compounding annualized return benchmarks
    earliest_date = df['datetime'].min()
    latest_trade_date = df_trades['exit_date'].max()
    time_delta = latest_trade_date - earliest_date
    years = time_delta.total_seconds() / (365.25 * 24 * 3600)  # Accurate fractional year calculation

    ending_balance = initial_balance + back_test_results['total income']

    # Mathematical metric logic allocations
    if years > 0 and ending_balance > 0:
        # Compute Compound Annual Growth Rate (CAGR)
        cagr = (ending_balance / initial_balance) ** (1 / years) - 1
        back_test_results['cagr'] = cagr * 100
        back_test_results['time span'] = years
        back_test_results['back test time start'] = earliest_date
        back_test_results['back test time end'] = latest_trade_date

        # Compute per-trade returns percent arrays
        df_trades['return_pct'] = df_trades['profit'] / initial_balance
        avg_trade_return = df_trades['return_pct'].mean()
        std_trade_return = df_trades['return_pct'].std()

        # Compute standard and annualized Sharpe Risk Ratios
        if std_trade_return > 0:
            base_sharpe = avg_trade_return / std_trade_return
            trades_per_year = len(df_trades) / years
            annualized_sharpe = base_sharpe * np.sqrt(trades_per_year)

            back_test_results['base_sharpe'] = base_sharpe
            back_test_results['annualized_sharpe'] = annualized_sharpe
        else:
            back_test_results['base_sharpe'] = 0.0
            back_test_results['annualized_sharpe'] = 0.0

        # Compute standard and annualized Sortino Downside Risk Ratios
        downside_returns = df_trades.loc[df_trades['return_pct'] < 0, 'return_pct']
        std_downside_return = np.sqrt(np.mean(downside_returns ** 2))
        if std_downside_return > 0:
            base_sortino = avg_trade_return / std_downside_return
            back_test_results['base_sortino'] = base_sortino
            back_test_results['annualized_sortino'] = base_sortino * np.sqrt(trades_per_year)
        else:
            back_test_results['base_sortino'] = 0.0
            back_test_results['annualized_sortino'] = 0.0
    else:
        # Fallback padding parameters for bankrupt/unexecuted simulation runs
        back_test_results['cagr'] = 0.0
        back_test_results['time span'] = years
        back_test_results['base_sharpe'] = 0.0
        back_test_results['annualized_sharpe'] = 0.0
        back_test_results['base_sortino'] = 0.0
        back_test_results['annualized_sortino'] = 0.0

    return back_test_results

def back_tester_results(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):
    """
        Executes back_tester and outputs formatted terminal summary metrics visualizations.

        Parameters:
        -----------
        strategy : Strategy.Strategy
            An instance of the trading strategy logic defining execution criteria blocks.
        symbol : str, optional
            The financial ticker asset symbol (default is 'EURUSD').
        time_frame : str, optional
            The candlestick timeline bar interval length (default is '1m').

        Returns:
        --------
        None
            Prints execution reports directly to stdout data buffers and invokes plot charts.
    """
    # Trigger simulation runner
    results = back_tester(strategy, symbol, time_frame)

    if results['Trades data'].empty:
        print('Seems this strategy not generated any signals, for accurate inspection, checking logs is highly recommended')
    else:
        # Format terminal logging performance interface tables
        print("\n" + "=" * 50 + "\nBACKTEST PERFORMANCE SUMMARY\n" + "=" * 50)
        print(f"Profit factor:             {results['profit factor']:.2f}")
        print(f"ROI is:                    {results['roi']:.1f}%")
        print(f"Backtest Horizon:          {results['time span']:.2f} years")
        print(f"Timeline Window:           {results['back test time start']} to {results['back test time end']}")
        print(f"CAGR:                      {results['cagr']:.2f}%")
        print(f"Base Sharpe (Per-Trade):   {results.get('base_sharpe', 0.0):.3f}")
        print(f"Annualized Sharpe Ratio:   {results.get('annualized_sharpe', 0.0):.3f}")
        print(f"Base Sortino (Per-Trade):  {results.get('base_sortino', 0.0):.3f}")
        print(f"Annualized Sortino Ratio:  {results.get('annualized_sortino', 0.0):.3f}")
        print("=" * 50 + "\n")

        # Display the generated financial charts window
        results['profit to time chart'].show()