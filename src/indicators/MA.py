import pandas as pd

def add_sma(df: pd.DataFrame, interval: int, inplace: bool =True, price_col: str ='close'):
    """
    Add a Simple Moving Average (SMA) column to a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    interval : int
        SMA period.
    inplace : bool, default=True
        If True, modify the original DataFrame.
        If False, return a modified copy.
    price_col : str, default='close'
        Column used to calculate the SMA.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the SMA column.
    """

    target_df = df if inplace else df.copy()

    target_df[f'MA_{interval}'] = (
        target_df[price_col]
        .rolling(window=interval)
        .mean()
    )

    return target_df

def add_ema(df: pd.DataFrame, interval: int, inplace: bool = True, price_col: str = 'close'):
    """
    Add an Exponential Moving Average (EMA) column to a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    interval : int
        EMA period (e.g., 10 for EMA 10).
    inplace : bool, default=True
        If True, modify the original DataFrame.
        If False, return a modified copy.
    price_col : str, default='close'
        Column used to calculate the EMA.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the EMA column.
    """
    # Determine the target DataFrame based on the inplace parameter
    target_df = df if inplace else df.copy()

    # Calculate EMA using Pandas ewm (Exponential Weighted Functions)
    # adjust=False ensures the calculation matches MetaTrader 5 and TradingView precisely
    target_df[f'EMA_{interval}'] = (
        target_df[price_col]
        .ewm(span=interval, adjust=False)
        .mean()
    )

    return target_df