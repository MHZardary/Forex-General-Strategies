import numpy as np
import pandas as pd
from tqdm import tqdm
from src.strategies import Strategy
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime

# Initialize file structure configurations for diagnostics
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
# Generate a uniquely timestamped log file filename per session
log_filename = os.path.join(LOG_DIR, f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Setup the logging framework hierarchy (Disables root print echoing automatically)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8")
    ]
)
logger = logging.getLogger("backtester_logger")

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
    path = os.path.join("data", "raw", file_name)

    logger.info(f"Initiating data ingestion pipeline for file: {path}")

    # Import MT5 exported data using standard tab-separated formatting
    try:
        df = pd.read_csv(path, sep="\t")
    except FileNotFoundError:
        logger.error(f"Historical data source file not found at path location: {path}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Failed to read data stream from storage file {path}: {str(e)}")
        return pd.DataFrame()

    # Clean header metadata brackets safely
    df.columns = df.columns.str.replace('<', '', regex=False).str.replace('>', '', regex=False)

    # Validate that all primary required columns are fully present in the source matrix
    required_cols = {'DATE', 'TIME', 'OPEN', 'HIGH', 'LOW', 'CLOSE'}
    if not required_cols.issubset(df.columns):
        logger.error(f"Source dataset columns at {path} are missing required standard MT5 headers.")
        return pd.DataFrame()

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
    try:
        df['datetime'] = pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format="%Y.%m.%d %H:%M:%S",
        )
    except Exception as e:
        print(f"[Error] Datetime parsing conversion failed for {symbol}: {str(e)}")
        return pd.DataFrame()

    logger.info(f"Successfully loaded and standardized {len(df)} records for asset {symbol}.")
    return df

def back_tester(strategy: Strategy.Strategy, symbol: str = 'EURUSD', time_frame: str = '1m'):
    """
    Simulates historical trading performance over time-series datasets and calculates
    advanced portfolio risk, frequency, and statistical expectancy metrics.

    Parameters:
    -----------
    strategy : Strategy.Strategy
        An instance of the trading strategy logic defining min_bars_required,
        calculate_signal, and execution continuity types.
    symbol : str, optional
        The financial ticker asset symbol to load from local storage streams
        (default is 'EURUSD').
    time_frame : str, optional
        The candlestick timeline bar interval length matching raw files
        (default is '1m').

    Returns:
    --------
    dict
        A comprehensive summary dictionary populated with execution records, performance
        visualizations, and advanced quantitative risk attributes:

        - 'symbol' (str): Asset identifier ticker string.
        - 'time frame' (str): Core operational bar horizon.
        - 'Financial data' (pd.DataFrame): The fully cleaned, standardized source market feed.
        - 'Trades data' (pd.DataFrame): Chronological transactional summary matrix tracking
          entry/exit timestamps, filled execution prices, directions, and equity steps.
        - 'time span' (float): The total fraction of historical test years simulated.
        - 'back test time start' (pd.Timestamp): Date-timestamp coordinate of the initial bar.
        - 'back test time end' (pd.Timestamp): Closing timestamp of the last processed position.
        - 'max_drawdown' (float): Peak-to-trough absolute risk percentage evaluated across
          the entire equity timeline, including initial capital baseline thresholds.
        - 'hit_rate' (float): Frequency percentage ratio of net-profitable closed trades.
        - 'win_rate' (float): Volumetric percentage ratio comparing gross monetary winning volume
          directly against total absolute dollar variances across all trades.
        - 'expectancy' (float): The mathematical profit expectancy value (R-multiple)
          generated per standard execution round.
        - 'turnover' (float): Annualized frequency density indicating total trades filled per year.
        - 'profit factor' (float): Absolute gross payout ratio of aggregate wins over aggregate losses.
        - 'total income' (float): Absolute net currency performance balance variation.
        - 'roi' (float): Return on investment percentage expansion calculated from inception base.
        - 'cagr' (float): Compounded Annual Growth Rate adjusting for simulated test duration.
        - 'base_sharpe' / 'annualized_sharpe' (float): Risk-adjusted reward metrics measuring returns
          per unit of portfolio standard deviation volatility.
        - 'base_sortino' / 'annualized_sortino' (float): Risk-adjusted reward metrics tracking excess
          performance solely against negative downside tracking variances.
        - 'profit to time chart' (matplotlib.pyplot): Multi-layered transactional and accumulated equity
          curve progression layout model.
    """
    logger.info(f"Initializing simulation backtest engine routine for Symbol: {symbol} ({time_frame})")
    back_test_results = {'symbol': symbol, 'time frame': time_frame, 'Financial data': pd.DataFrame()}

    # Ingest full historical series
    df = data_loader(symbol, time_frame)
    if df.empty:
        logger.error(f"Empty dataset returned for asset context {symbol}. Cancelling backtest.")
        return back_test_results

    back_test_results['Financial data'] = df

    # Guard Condition: Ensure database context size satisfies lookback requirements
    if len(df) <= strategy.min_bars_required:
        logger.error(f"Data length ({len(df)}) is insufficient for strategy lookback requirement window ({strategy.min_bars_required}).")
        return back_test_results

    current_position = 0
    long_price = []
    short_price = []

    logger.info("Chronological historical processing tracking started...")
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
                logger.info(f"[{dt}] Logic Execution -> Long Closed out at price: {current_close}")
                current_position = 0

                # Continuous Reversal: Instantly enter opposite short asset state
                if strategy.is_continuous and signal == -1:
                    short_price.append([[current_close, dt], None])
                    logger.info(f"[{dt}] Reversal Triggered -> Immediate Short entry at price: {current_close}")
                    current_position = -1

        # Short state execution management logic
        elif current_position == -1:
            if signal == 2 or signal == 1:
                # Close out open active short position array row
                if len(short_price) > 0:
                    short_price[-1][-1] = [current_close, dt]
                logger.info(f"[{dt}] Logic Execution -> Short Closed out at price: {current_close}")
                current_position = 0

                # Continuous Reversal: Instantly enter opposite long asset state
                if strategy.is_continuous and signal == 1:
                    long_price.append([[current_close, dt], None])
                    logger.info(f"[{dt}] Reversal Triggered -> Immediate Long entry at price: {current_close}")
                    current_position = 1

            # Flat structural execution condition rules
        else:
            if signal == 1:
                long_price.append([[current_close, dt], None])
                logger.info(f"[{dt}] Execution Entry -> Long Triggered at price: {current_close}")
                current_position = 1
            elif signal == -1:
                short_price.append([[current_close, dt], None])
                logger.info(f"[{dt}] Execution Entry -> Short Triggered at price: {current_close}")
                current_position = -1

    # Clean up unclosed trailing positions at the terminal edge of the dataset
    if len(short_price) > 0 and short_price[-1][1] is None:
        logger.info("Trimming unclosed trailing sell position at endpoint edge.")
        short_price = short_price[:-1]
    if len(long_price) > 0 and long_price[-1][1] is None:
        logger.info("Trimming unclosed trailing buy position at endpoint edge.")
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
        logger.warning(f"Strategy did not populate any execution signal flags for ticker context: {symbol}.")
        return back_test_results

    # Order positions chronologically by execution entry timestamp
    df_trades = df_trades.sort_values("entry_date").reset_index(drop=True)
    initial_balance = 100.0

    # Calculate absolute returns and raw cumulative profit vectors
    df_trades['price_change'] = df_trades['exit_price'] - df_trades['entry_price']
    df_trades['profit'] = df_trades['price_change'] * df_trades['direction'] * 10
    df_trades["cum_profit"] = df_trades["profit"].cumsum()
    df_trades["equity"] = initial_balance + df_trades["cum_profit"]

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

        # Maximum Drawdown Calculation (Peak-to-Trough)
        equity_series = df_trades["equity"].tolist()
        # Prepend initial balance to evaluate drawdown profile from inception point
        full_equity_curve = [initial_balance] + equity_series

        running_peak = full_equity_curve[0]
        max_drawdown = 0.0

        for eq_value in full_equity_curve:
            if eq_value > running_peak:
                running_peak = eq_value
            dd = (running_peak - eq_value) / running_peak
            if dd > max_drawdown:
                max_drawdown = dd

        back_test_results['max_drawdown'] = max_drawdown * 100

        # Hit Rate and Win Rate Metric Extractions
        winning_trades = df_trades[df_trades['profit'] > 0]
        losing_trades = df_trades[df_trades['profit'] < 0]
        total_trades_count = len(df_trades)

        raw_hit_rate = len(winning_trades) / total_trades_count if total_trades_count > 0 else 0.0
        back_test_results['hit_rate'] = raw_hit_rate * 100  # Saved as percentage for display

        sum_profits = winning_trades['profit'].sum()
        sum_losses = abs(losing_trades['profit'].sum())

        win_rate = (sum_profits / (sum_profits + sum_losses)) * 100 if (sum_profits + sum_losses) > 0 else 0.0
        back_test_results['win_rate'] = win_rate

        # Mathematical System Expectancy (R) Calculation
        avg_win = winning_trades['profit'].mean() if len(winning_trades) > 0 else 0.0
        avg_loss = abs(losing_trades['profit'].mean()) if len(losing_trades) > 0 else 0.0

        # Correctly uses the decimal format
        probability_loss = 1.0 - raw_hit_rate

        # Expectancy now accurately reflects average return per trade
        expectancy = (raw_hit_rate * avg_win) - (probability_loss * avg_loss)
        back_test_results['expectancy'] = expectancy

        # Strategy Equity Turnover Rate (Annualized Execution Density)
        turnover = total_trades_count / years if years > 0 else 0.0
        back_test_results['turnover'] = turnover

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

    logger.info(f"Backtest process terminated smoothly for symbol: {symbol}. Data tracked to summary structure objects.")
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

    if 'Trades data' not in results or results['Trades data'].empty:
        print('Seems this strategy not generated any signals, for accurate inspection, checking logs is highly recommended')
    else:
        # Format terminal logging performance interface tables
        print("\n" + "=" * 50 + "\nPERFORMANCE SUMMARY\n" + "=" * 50)
        print(f"Profit Factor:             {results.get('profit factor', 0.0):.2f}")
        print(f"ROI Percentage:            {results.get('roi', 0.0):.1f}%")
        print(f"CAGR Growth Rate:          {results.get('cagr', 0.0):.2f}%")
        print(f"Maximum Drawdown:          {results.get('max_drawdown', 0.0):.2f}%")
        print(f"System Hit Rate:           {results.get('hit_rate', 0.0):.1f}%")
        print(f"System Win Rate:           {results.get('win_rate', 0.0):.1f}%")
        print(f"Expectancy (Avg R-$):      {results.get('expectancy', 0.0):.2f}")
        print(f"Annual Turnover Rate:      {results.get('turnover', 0.0):.1f} trades/yr")
        print("-" * 50)
        print(f"Backtest Horizon:          {results.get('time span', 0.0):.2f} years")
        print(
            f"Timeline Window:           {results.get('back test time start')} to {results.get('back test time end')}")
        print(f"Annualized Sharpe Ratio:   {results.get('annualized_sharpe', 0.0):.3f}")
        print(f"Annualized Sortino Ratio:  {results.get('annualized_sortino', 0.0):.3f}")
        print("=" * 50 + "\n")

        if 'profit to time chart' in results and results['profit to time chart'] is not None:
            results['profit to time chart'].show()