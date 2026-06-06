import pandas as pd
import mplfinance as mpf

def plot_price_indicators(df, sma_periods=None, rsi_periods=None, last_n=200, title="Price Chart with Indicators", style_name="nightclouds"):
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
