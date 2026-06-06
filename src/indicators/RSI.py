import pandas as pd

def add_rsi(df: pd.DataFrame, interval: int =14, inplace: bool =True, price_col: str ='Close'):
    """
    Add an RSI column to a DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame.
    interval : int, default=14
        RSI period.
    inplace : bool, default=True
        If True, modify the original DataFrame.
        If False, return a modified copy.
    price_col : str, default='Close'
        Column used to calculate RSI.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the RSI column.
    """

    target_df = df if inplace else df.copy()

    delta = target_df[price_col].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=interval).mean()
    avg_loss = loss.rolling(window=interval).mean()

    rs = avg_gain / avg_loss

    target_df[f'RSI_{interval}'] = 100 - (100 / (1 + rs))

    return target_df