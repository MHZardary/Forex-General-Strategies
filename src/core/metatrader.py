import time
import MetaTrader5 as mt5
import pandas as pd

def update_candle_dataframe(df, symbol, timeframe, n_max):
    """Checks for a new closed candle.

    If found, appends it to 'df' and caps the total rows at 'n_max'.
    """
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, 1)

    if rates is None or len(rates) == 0:
        return 0

    new_candle_time = pd.to_datetime(rates[0]["time"], unit="s")

    if df.empty:
        initial_rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, n_max)
        df = pd.DataFrame(initial_rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]
        return df

    if new_candle_time > df["time"].max():
        new_row = pd.DataFrame(rates)
        new_row["time"] = pd.to_datetime(new_row["time"], unit="s")
        new_row = new_row[["time", "open", "high", "low", "close", "tick_volume"]]
        df = pd.concat([df, new_row], ignore_index=True)

        if len(df) > n_max:
            df = df.iloc[-n_max:].reset_index(drop=True)

    return df

def get_account_balance():
    """Fetches the current account balance from the connected MT5 terminal.

    Assumes mt5.initialize() has already been called externally.

    Returns:
        float: The account balance if successful, None otherwise.
    """
    account_info = mt5.account_info()

    if account_info is None:
        return None

    return account_info.balance

def get_positions_summary(symbol):
    """Counts the total number and total lot sizes for BUY and SELL positions

    separately for a given symbol.
    """
    # Initialize the summary dictionary
    summary = {"buy_count": 0, "buy_lots": 0.0, "sell_count": 0, "sell_lots": 0.0}

    # Fetch open positions for the specific symbol
    positions = mt5.positions_get(symbol=symbol)

    if positions is None:
        print(f"Error fetching positions. Error code: {mt5.last_error()}")
        return summary

    # Iterate through all open positions and filter by type
    for pos in positions:
        if pos.type == mt5.POSITION_TYPE_BUY:
            summary["buy_count"] += 1
            summary["buy_lots"] += pos.volume

        elif pos.type == mt5.POSITION_TYPE_SELL:
            summary["sell_count"] += 1
            summary["sell_lots"] += pos.volume

    # Round lot sizes to 2 decimal places to avoid Python floating-point issues
    summary["buy_lots"] = round(summary["buy_lots"], 2)
    summary["sell_lots"] = round(summary["sell_lots"], 2)

    return summary

def close_market_positions(symbol, side_to_close="all"):
    """Closes open positions for a specific symbol.

    Args:
        symbol (str): The market symbol (e.g., "EURUSD").
        side_to_close (str): Options are 'buy' to close only buy positions,
          'sell' to close only sell positions, or 'all' to close everything.

    Returns:
        bool: True if all targeted positions were processed, False otherwise.
    """
    # 1. Fetch all open positions for the symbol
    positions = mt5.positions_get(symbol=symbol)

    if positions is None:
        print(f"No positions found or error occurred: {mt5.last_error()}")
        return False

    if len(positions) == 0:
        print(f"No open positions to close for {symbol}.")
        return True

    # Normalize input string to lowercase
    side_to_close = side_to_close.lower()
    all_successful = True

    # 2. Iterate through each open position
    for pos in positions:
        # Filter based on the side requested
        if side_to_close == "buy" and pos.type != mt5.POSITION_TYPE_BUY:
            continue
        if side_to_close == "sell" and pos.type != mt5.POSITION_TYPE_SELL:
            continue

        # Get fresh tick data to ensure an accurate close price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Failed to get tick data for {symbol} while closing.")
            all_successful = False
            continue

        # 3. Determine the opposite order type and appropriate execution price
        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid  # Close a Buy at the Bid price
        elif pos.type == mt5.POSITION_TYPE_SELL:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask  # Close a Sell at the Ask price
        else:
            continue

        # 4. Build the trade close request dictionary
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,  # Full volume of the current position
            "type": order_type,
            "position": pos.ticket,  # CRITICAL: Links the execution to the open position
            "price": price,
            "deviation": 20,  # Max slippage tolerance in points
            "magic": 0,
            "comment": "Python closing script",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # 5. Send the execution order to MetaTrader 5
        result = mt5.order_send(close_request)

        # Check if the broker accepted the deal
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(
                f"Failed to close position #{pos.ticket}. Error: {result.comment} (Code: {result.retcode})"
            )
            all_successful = False
        else:
            print(
                f"Successfully closed position #{pos.ticket} ({pos.volume} lots)"
            )

    return all_successful

def open_market_position(symbol, order_type, volume, deviation=20, magic=0):
    """Opens a market position (BUY or SELL) for a specified symbol and volume.

    Args:
        symbol (str): The trading pair/asset (e.g., "EURUSD").
        order_type (str): Direction to trade, either 'buy' or 'sell'.
        volume (float): The trade volume (lot size), e.g., 0.1, 1.0.
        deviation (int): Maximum price slippage allowed in points.
        magic (int): Optional ID number to tag your bot's trades.

    Returns:
        OrderSendResult or None: The MT5 response object if processed, or None
        if failed.
    """
    # 1. Standardize direction string to lowercase
    direction = order_type.lower()

    # 2. Fetch live pricing info to get accurate Ask/Bid execution targets
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(
            f"Failed to fetch tick data for {symbol}. Error: {mt5.last_error()}"
        )
        return None

    # 3. Assign internal MT5 order constants and matching execution prices
    if direction == "buy":
        mt5_order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
    elif direction == "sell":
        mt5_order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        print(f"Invalid direction '{order_type}'. Use 'buy' or 'sell'.")
        return None

    # 4. Construct the trade deal request configuration dictionary
    trade_request = {
        "action": mt5.TRADE_ACTION_DEAL,  # Type of trade operation (Immediate Execution)
        "symbol": symbol,
        "volume": float(volume),
        "type": mt5_order_type,
        "price": price,
        "deviation": deviation,
        "magic": magic,
        "comment": "Python execution script",
        "type_time": mt5.ORDER_TIME_GTC,  # Good 'til Cancelled
        "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel filling mode
    }

    # 5. Route the request through the open MT5 terminal link
    result = mt5.order_send(trade_request)

    # 6. Verify trade confirmation from broker
    if result is None:
        print(f"Order submission failed drastically: {mt5.last_error()}")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(
            f"Trade Execution Failed. Broker Rejected. Code: {result.retcode} ({result.comment})"
        )
    else:
        print(
            f"Successfully opened {direction.upper()} | Ticket #{result.order} | Lots: {volume}"
        )

    return result