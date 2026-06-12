import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime

# Initialize file system workspace directories dynamically
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Generate a cleanly tracked log file footprint for this specific core session instance
log_filename = os.path.join(LOG_DIR, f"terminal_execution_{datetime.now().strftime('%Y%m%d')}.log")

# Setup the system configuration parameters (Ensuring no default console print streaming occurs)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8")
    ]
)
logger = logging.getLogger("mt5_core_logger")


def update_candle_dataframe(df, symbol, timeframe, n_max):
    """
    Checks for a new closed candle. If found, appends it to 'df' and caps the total rows at 'n_max'.

    Parameters:
    -----------
    df : pd.DataFrame
        The existing historical candlestick matrix data buffer.
    symbol : str
        The financial asset ticker symbol (e.g., 'EURUSD').
    timeframe : int
        The MT5 timeframe constant (e.g., mt5.TIMEFRAME_M1).
    n_max : int
        The maximum number of rows to keep in the historical buffer.

    Returns:
    --------
    pd.DataFrame or int
        Returns the updated pandas DataFrame containing historical candle data,
        or 0 if the data fetch fails.
    """
    try:
        # Fetch the most recently completed historical candle bar
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, 1)

        # Handle terminal connection drops or missing market feed assets defensively
        if rates is None or len(rates) == 0:
            logger.warning(f"Failed to fetch current rates for {symbol}. MT5 Error: {mt5.last_error()}")
            return 0

        # Parse numerical timestamp into a standard datetime object
        new_candle_time = pd.to_datetime(rates[0]["time"], unit="s")
        required_columns = ["time", "open", "high", "low", "close", "tick_volume"]

        # Cold Warmup: Populate full database slice if dataframe buffer is uninitialized
        if df is None or df.empty:
            initial_rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, n_max)
            if initial_rates is None or len(initial_rates) == 0:
                logger.error(f"Initialization failed. Cannot warmup history for {symbol}.")
                return 0

            df = pd.DataFrame(initial_rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            # Guard against structural metadata adjustments by the broker platform
            if not set(required_columns).issubset(df.columns):
                logger.error(f"Unexpected data format returned from MT5 for symbol: {symbol}")
                return 0

            df = df[required_columns]
            logger.info(f"Successful cold warmup historical data frame for asset: {symbol}")
            return df

        # Real-Time Append: Push the newest candle row if the bar interval timestamp has progressed
        if new_candle_time > df["time"].max():
            new_row = pd.DataFrame(rates)
            new_row["time"] = pd.to_datetime(new_row["time"], unit="s")
            new_row = new_row[required_columns]
            df = pd.concat([df, new_row], ignore_index=True)

            # Dynamic Memory Management: Trim oldest records exceeding memory allocation targets
            if len(df) > n_max:
                df = df.iloc[-n_max:].reset_index(drop=True)

            logger.info(f"New closed candle appended for {symbol} at timestamp: {new_candle_time}")

        return df

    except Exception as e:
        logger.critical(f"Failed updating dataframe for {symbol}: {str(e)}")
        return 0

def get_account_balance():
    """
    Fetches the current account balance from the connected MT5 terminal.

    Assumes mt5.initialize() has already been called externally.

    Returns:
    --------
    float or None
        The current account balance currency value if successful, None otherwise.
    """
    try:
        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"Could not fetch account info. Terminal disconnected. Code: {mt5.last_error()}")
            return None
        return account_info.balance
    except Exception as e:
        logger.critical(f"Error reading account metrics data: {str(e)}")
        return None

def get_positions_summary(symbol):
    """
    Counts the total number and total lot sizes for BUY and SELL positions separately for a given symbol.

    Parameters:
    -----------
    symbol : str
        The financial asset ticker symbol (e.g., 'EURUSD').

    Returns:
    --------
    dict
        A summary dictionary tracking transaction count maps and volume lot distributions.
    """
    summary = {"buy_count": 0, "buy_lots": 0.0, "sell_count": 0, "sell_lots": 0.0}

    try:
        # Fetch live execution parameters from active terminal server streams
        positions = mt5.positions_get(symbol=symbol)

        # Distinguish between an empty market tracker state and a terminal error disconnect
        if positions is None:
            err_code = mt5.last_error()
            if err_code != mt5.RES_穩_OK:  # Filter genuine communication crashes
                logger.error(f"Terminal communication broken for {symbol}. Code: {err_code}")
            return summary

        # Separate total volumetric and item values into execution vectors
        for pos in positions:
            if pos.type == mt5.POSITION_TYPE_BUY:
                summary["buy_count"] += 1
                summary["buy_lots"] += pos.volume
            elif pos.type == mt5.POSITION_TYPE_SELL:
                summary["sell_count"] += 1
                summary["sell_lots"] += pos.volume

        # Round floating numbers to eliminate precision drift across allocation vectors
        summary["buy_lots"] = round(summary["buy_lots"], 2)
        summary["sell_lots"] = round(summary["sell_lots"], 2)
        return summary

    except Exception as e:
        logger.critical(f"Failed compiling open position summary profiles for {symbol}: {str(e)}")
        return summary

def close_market_positions(symbol, side_to_close="all"):
    """
    Closes open positions for a specific symbol.

    Parameters:
    -----------
    symbol : str
        The market symbol (e.g., "EURUSD").
    side_to_close : str, optional
        Filter choice: 'buy' for longs, 'sell' for shorts, or 'all' for complete liquidation (default is 'all').

    Returns:
    --------
    bool
        True if all targeted positions were processed successfully, False otherwise.
    """
    try:
        positions = mt5.positions_get(symbol=symbol)

        if positions is None:
            logger.error(f"Failed to read open data records to liquidate. Code: {mt5.last_error()}")
            return False

        if len(positions) == 0:
            return True

        side_to_close = side_to_close.lower()
        all_successful = True

        # Liquidation Loop: Iterate over open transactions
        for pos in positions:
            if side_to_close == "buy" and pos.type != mt5.POSITION_TYPE_BUY:
                continue
            if side_to_close == "sell" and pos.type != mt5.POSITION_TYPE_SELL:
                continue

            # Refresh pricing info to maximize fill execution accuracy
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Liquidation price snapshot dropped for {symbol}. Skipping ticket #{pos.ticket}")
                all_successful = False
                continue

            # Counter-Trade Valuation: Target opposite asset values to close out exposure
            if pos.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            elif pos.type == mt5.POSITION_TYPE_SELL:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                continue

            # Format trade close out dictionary request payload
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": pos.ticket,  # Critical link connection reference ID
                "price": price,
                "deviation": 20,
                "magic": 0,
                "comment": "Python closing script",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Dispatch transmission block directly to MT5 order server terminal
            result = mt5.order_send(close_request)

            # Defensive Check: Handle total connection or communication losses during dispatch
            if result is None:
                logger.error(f"Order routing failed entirely for close out ticket #{pos.ticket}. Code: {mt5.last_error()}")
                all_successful = False
                continue

            # Confirm settlement feedback codes are correct
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Broker denied close order #{pos.ticket}. Reason: {result.comment} (Code: {result.retcode})")
                all_successful = False
            else:
                logger.info(f"Successfully closed position #{pos.ticket} ({pos.volume} lots)")

        return all_successful

    except Exception as e:
        logger.critical(f"Position liquidation process failed completely for {symbol}: {str(e)}")
        return False

def open_market_position(symbol, order_type, volume, deviation=20, magic=0):
    """
    Opens a market position (BUY or SELL) for a specified symbol and volume.

    Parameters:
    -----------
    symbol : str
        The trading pair/asset (e.g., "EURUSD").
    order_type : str
        Direction to trade, either 'buy' or 'sell'.
    volume : float
        The trade volume (lot size), e.g., 0.1, 1.0.
    deviation : int, optional
        Maximum price slippage allowed in points (default is 20).
    magic : int, optional
        Optional ID number to tag your bot's trades (default is 0).

    Returns:
    --------
    OrderSendResult or None
        The MT5 response structure object if processed, or None if failed.
    """
    try:
        direction = order_type.lower()

        # Synchronize fast real-time ticking values
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Real-time market tick pricing stream missing for {symbol}. Code: {mt5.last_error()}")
            return None

        # Structural Routing: Match trade directions to corresponding order book limits
        if direction == "buy":
            mt5_order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif direction == "sell":
            mt5_order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            logger.error(f"Invalid order side parameter string passed: '{order_type}'")
            return None

        # Construct execution transaction specifications payload
        trade_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": mt5_order_type,
            "price": price,
            "deviation": deviation,
            "magic": magic,
            "comment": "Python execution script",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Dispatch market request transaction to your broker network
        result = mt5.order_send(trade_request)

        # Defensive Check: Secure module from crashing on server connection timeouts
        if result is None:
            logger.error(f"Request dropped silently by network routing layer. Code: {mt5.last_error()}")
            return None

        # Check broker processing status codes before confirming trade locally
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Broker rejected trade deal entry. Code: {result.retcode} ({result.comment})")
        else:
            logger.info(f"Successfully opened {direction.upper()} | Ticket #{result.order} | Lots: {volume}")

        return result

    except Exception as e:
        logger.critical(f"Trade setup execution pipeline broke unexpectedly: {str(e)}")
        return None