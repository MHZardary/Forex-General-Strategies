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