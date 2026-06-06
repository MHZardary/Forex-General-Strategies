import pandas as pd
import mplfinance as mpf

def add_sma(df, interval, inplace=True, price_col='Close'):
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
    price_col : str, default='Close'
        Column used to calculate the SMA.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the SMA column.
    """

    target_df = df if inplace else df.copy()

    target_df[f'SMA_{interval}'] = (
        target_df[price_col]
        .rolling(window=interval)
        .mean()
    )

    return target_df

def add_rsi(df, interval=14, inplace=True, price_col='Close'):
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


def plot_price_indicators(
    df,
    sma_periods=None,
    rsi_periods=None,
    last_n=200,
    title="Price Chart with Indicators",
    style_name="nightclouds"
):
    """
    Plot candlesticks with SMA and RSI indicators using mplfinance.
    """

    sma_periods = sma_periods or []
    rsi_periods = rsi_periods or []

    plot_df = df.copy()

    # --------------------------------------------------
    # 1. Ensure DatetimeIndex (required by mplfinance)
    # --------------------------------------------------
    if not isinstance(plot_df.index, pd.DatetimeIndex):
        if 'Date' in plot_df.columns and 'Time' in plot_df.columns:
            plot_df['Datetime'] = pd.to_datetime(
                plot_df['Date'] + ' ' + plot_df['Time']
            )
            plot_df.set_index('Datetime', inplace=True)
        else:
            raise ValueError("DataFrame must have Date/Time columns or a DatetimeIndex")

    # --------------------------------------------------
    # 2. Sort index (important for financial df)
    # --------------------------------------------------
    plot_df.sort_index(inplace=True)

    # --------------------------------------------------
    # 3. Slice last N candles
    # --------------------------------------------------
    plot_df = plot_df.tail(last_n)

    # --------------------------------------------------
    # 4. Create custom dark style
    # --------------------------------------------------
    custom_style = mpf.make_mpf_style(
        base_mpf_style=style_name,
        marketcolors=mpf.make_marketcolors(
            up='green',
            down='red',
            edge='inherit',
            wick='inherit',
            volume='inherit'
        )
    )

    # --------------------------------------------------
    # 5. Build indicators
    # --------------------------------------------------
    addplots = []

    # SMA overlays (price panel)
    for period in sma_periods:
        col = f"SMA_{period}"
        if col in plot_df.columns:
            addplots.append(mpf.make_addplot(plot_df[col]))

    # RSI panels
    panel = 1
    for period in rsi_periods:
        col = f"RSI_{period}"

        if col in plot_df.columns:
            addplots.append(
                mpf.make_addplot(
                    plot_df[col],
                    panel=panel,
                    ylabel=f"RSI {period}"
                )
            )

            # Overbought / oversold lines
            addplots.append(
                mpf.make_addplot([70] * len(plot_df), panel=panel)
            )
            addplots.append(
                mpf.make_addplot([30] * len(plot_df), panel=panel)
            )

            panel += 1

    # --------------------------------------------------
    # 6. Final plot
    # --------------------------------------------------
    mpf.plot(
        plot_df,
        type='candle',
        style=custom_style,
        volume=False,
        addplot=addplots,
        figsize=(14, 8),
        title=title
    )

df = pd.read_csv(r"data\raw\EURUSD_M1.csv", sep="\t")

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

add_sma(df, 20)
add_sma(df, 200)
add_rsi(df)

plot_price_indicators(
    df,
    sma_periods=[20, 200],
    rsi_periods=[14],
    last_n=60
)