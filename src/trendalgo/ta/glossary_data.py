"""Comprehensive TA-Lib glossary entries used by the UI tooltips."""

from __future__ import annotations

import re

from trendalgo.ta.catalog import TA_FUNCTION_NAMES

_LINK_RE = re.compile(r"\[\[[A-Z0-9_]+(?:\|[^\]]+)?\]\]")


def _lower_preserve_links(text: str) -> str:
    """Lowercase prose while keeping [[ID|label]] link markup intact."""
    parts: list[str] = []
    last = 0
    for match in _LINK_RE.finditer(text):
        parts.append(text[last : match.start()].lower())
        parts.append(match.group(0))
        last = match.end()
    parts.append(text[last:].lower())
    return "".join(parts)


def _entry(
    title: str,
    short: str,
    explain: str,
    tip: str,
    formula: str,
) -> dict[str, str]:
    return {
        "title": title,
        "short": short,
        "long": f"{explain} {tip}",
        "formula": formula,
    }


def _cdl_entry(title: str, shape: str, implication: str) -> dict[str, str]:
    short = f"{shape} Usually read as {implication}."
    long = (
        f"{title} is a candlestick pattern defined by candle body and wick geometry. "
        f"It appears when {_lower_preserve_links(shape)} Traders usually read it as {implication}. "
        "Use surrounding trend and volume as confirmation before acting."
    )
    return {
        "title": title,
        "short": short,
        "long": long,
        "formula": (
            "Rule-based OHLC pattern score from TA-Lib candlestick logic "
            "(+100 bullish, -100 bearish, 0 no pattern)."
        ),
    }


_NON_CDL: dict[str, dict[str, str]] = {
    "AD": _entry(
        "Chaikin A/D Line",
        "Cumulative money flow line using close location value and volume.",
        "The Accumulation/Distribution Line estimates whether volume is flowing into or out of an asset.",
        "Rising AD with rising price supports trend health, while divergence can warn of weakening momentum.",
        "AD_t = AD_(t-1) + [((C-L)-(H-C))/(H-L)] * Volume",
    ),
    "ADOSC": _entry(
        "Chaikin A/D Oscillator",
        "Momentum of the A/D Line from fast and slow EMA spread.",
        "ADOSC measures acceleration in accumulation/distribution by subtracting a slow AD EMA from a fast AD EMA.",
        "Positive values suggest increasing buying pressure, while negative values suggest increasing selling pressure.",
        "ADOSC = EMA_fast(AD) - EMA_slow(AD)",
    ),
    "ADX": _entry(
        "Average Directional Index",
        "Trend-strength gauge; direction is read from +DI and -DI.",
        "ADX smooths directional movement into a 0-100 trend-strength score.",
        "Many traders treat rising ADX as trend strengthening and falling ADX as trend exhaustion.",
        "ADX = WilderMA(DX, N), DX = 100 * |(+DI - -DI)/(+DI + -DI)|",
    ),
    "ADXR": _entry(
        "Average Directional Movement Rating",
        "Smoothed ADX that averages current and prior ADX values.",
        "ADXR reduces ADX noise by averaging the current ADX with an ADX value N periods back.",
        "It is useful when you want a slower trend-strength filter for systems with fewer trades.",
        "ADXR_t = (ADX_t + ADX_(t-N)) / 2",
    ),
    "APO": _entry(
        "Absolute Price Oscillator",
        "Difference between fast and slow moving averages in price units.",
        "APO shows how far short-term average price is above or below long-term average price.",
        "Crossing zero can indicate momentum regime shifts in trend-following systems.",
        "APO = MA_fast(price) - MA_slow(price)",
    ),
    "AROON": _entry(
        "Aroon Up/Down",
        "Tracks time since recent highs and lows to detect trend shifts.",
        "Aroon Up rises when new highs occur quickly, while Aroon Down rises when new lows occur quickly.",
        "Crossovers often mark transitions between bullish and bearish trend phases.",
        "AroonUp = 100*(N - periods_since_high)/N; AroonDown = 100*(N - periods_since_low)/N",
    ),
    "AROONOSC": _entry(
        "Aroon Oscillator",
        "Difference between Aroon Up and Aroon Down.",
        "Aroon Oscillator condenses Aroon signals into one line centered at zero.",
        "Positive values favor bullish trend pressure and negative values favor bearish pressure.",
        "AroonOsc = AroonUp - AroonDown",
    ),
    "ATR": _entry(
        "Average True Range",
        "Average of true range; common for stop and position sizing.",
        "ATR measures typical volatility by including price gaps in the range calculation.",
        "Higher ATR means wider market swings, which usually requires wider stops.",
        "TR = max(H-L, |H-C_prev|, |L-C_prev|); ATR = WilderMA(TR, N)",
    ),
    "AVGPRICE": _entry(
        "Average Price",
        "Simple average of OHLC for each bar.",
        "AVGPRICE gives a single representative price level for each candle using all four OHLC points.",
        "It is commonly used as a neutral input series for smoothing or oscillators.",
        "AVGPRICE = (O + H + L + C) / 4",
    ),
    "BBANDS": _entry(
        "Bollinger Bands",
        "Volatility bands around a moving average.",
        "Bollinger Bands widen when volatility rises and contract during quiet periods.",
        "Traders watch band squeezes for breakout setups and outer-band touches for mean reversion context.",
        "Middle = MA(C, N); Upper = Middle + k*STDDEV(C, N); Lower = Middle - k*STDDEV(C, N)",
    ),
    "BETA": _entry(
        "Beta Coefficient",
        "Relative volatility of one series versus another.",
        "Beta estimates how sensitive one asset is to moves in a comparison asset or benchmark.",
        "A beta above 1 implies amplified movement versus the benchmark; below 1 implies lower sensitivity.",
        "Beta = Covariance(x, y) / Variance(y)",
    ),
    "BOP": _entry(
        "Balance of Power",
        "Compares close-open distance to full bar range.",
        "BOP estimates whether buyers or sellers controlled each candle.",
        "Sustained positive readings suggest buyer control, while negative readings suggest seller control.",
        "BOP = (C - O) / (H - L)",
    ),
    "CCI": _entry(
        "Commodity Channel Index",
        "Deviation of typical price from its moving average.",
        "CCI measures how far price has moved away from its statistical mean.",
        "Values beyond +/-100 often mark unusually strong momentum that can continue or mean-revert.",
        "TP=(H+L+C)/3; CCI=(TP-SMA(TP,N)) / (0.015*MeanDeviation(TP,N))",
    ),
    "CMO": _entry(
        "Chande Momentum Oscillator",
        "Momentum oscillator based on sum of gains versus losses.",
        "CMO compares total up-move magnitude to down-move magnitude over the lookback.",
        "Readings near extremes indicate stretched momentum and possible reversals.",
        "CMO = 100*(SumGain - SumLoss)/(SumGain + SumLoss)",
    ),
    "CORREL": _entry(
        "Pearson Correlation Coefficient",
        "Rolling linear correlation between two series.",
        "CORREL shows whether two assets move together, opposite, or independently.",
        "Values near +1 imply strong positive co-movement, while values near -1 imply inverse behavior.",
        "CORREL = Cov(x,y) / (StdDev(x)*StdDev(y))",
    ),
    "DEMA": _entry(
        "Double Exponential Moving Average",
        "Fast moving average with reduced lag versus EMA.",
        "DEMA combines one EMA and a second EMA of that EMA to react quicker to trend changes.",
        "It can improve responsiveness, but may whipsaw more in choppy markets.",
        "DEMA = 2*EMA(price, N) - EMA(EMA(price, N), N)",
    ),
    "DX": _entry(
        "Directional Movement Index",
        "Raw trend-strength component used in ADX.",
        "DX compares separation between +DI and -DI as a percent of their sum.",
        "Higher values indicate clearer directional dominance in recent bars.",
        "DX = 100*|(+DI - -DI)/(+DI + -DI)|",
    ),
    "EMA": _entry(
        "Exponential Moving Average",
        "Moving average weighted toward recent prices.",
        "EMA responds faster than SMA because recent bars receive more weight.",
        "Many traders use EMA stacks and crossovers to define trend direction.",
        "EMA_t = alpha*Price_t + (1-alpha)*EMA_(t-1), alpha = 2/(N+1)",
    ),
    "HT_DCPERIOD": _entry(
        "Hilbert Transform Dominant Cycle Period",
        "Estimated dominant market cycle length in bars.",
        "This Hilbert output estimates the prevailing cycle period from phase information.",
        "Traders often adapt oscillator windows dynamically using this period estimate.",
        "DCPERIOD = Hilbert dominant cycle period estimate (TA-Lib Hilbert method)",
    ),
    "HT_DCPHASE": _entry(
        "Hilbert Transform Dominant Cycle Phase",
        "Estimated phase angle of the dominant cycle.",
        "Cycle phase helps identify where price sits within an inferred oscillation.",
        "Phase turning points are sometimes used to time momentum shifts.",
        "DCPHASE = Hilbert phase angle of dominant cycle",
    ),
    "HT_PHASOR": _entry(
        "Hilbert Transform Phasor Components",
        "In-phase and quadrature components of price cycle.",
        "HT_PHASOR returns two signals used to describe cycle rotation over time.",
        "The relationship between components can help identify cycle acceleration or deceleration.",
        "InPhase, Quadrature = Hilbert phasor transform outputs",
    ),
    "HT_SINE": _entry(
        "Hilbert Transform SineWave",
        "Sine and lead-sine cycle outputs from Hilbert transform.",
        "HT_SINE converts cycle phase into sinusoidal waveforms for turning-point analysis.",
        "Crosses between sine and lead-sine are often used as cycle-timing cues.",
        "Sine = sin(phase); LeadSine = sin(phase + 45deg)",
    ),
    "HT_TRENDLINE": _entry(
        "Hilbert Transform Instantaneous Trendline",
        "Adaptive trendline derived from Hilbert cycle processing.",
        "This line attempts to follow the market while accounting for cyclical behavior.",
        "It is often used as a dynamic baseline for trend-mode systems.",
        "InstantaneousTrendline = Hilbert adaptive trendline estimate",
    ),
    "HT_TRENDMODE": _entry(
        "Hilbert Transform Trend vs Cycle Mode",
        "Binary regime flag: trending or cycling.",
        "HT_TRENDMODE tries to classify whether price action is better described as trend or cycle.",
        "Regime filters can improve strategy selection, such as trend-following versus mean reversion.",
        "TrendMode in {0,1} from Hilbert regime detection",
    ),
    "KAMA": _entry(
        "Kaufman Adaptive Moving Average",
        "Adaptive MA that speeds up in trends and slows in noise.",
        "KAMA uses an efficiency ratio to adjust smoothing based on market noisiness.",
        "It aims to track trends while reducing whipsaw in sideways periods.",
        "ER=|Price_t-Price_(t-N)|/Sum(|delta Price|,N); KAMA uses ER-scaled alpha",
    ),
    "LINEARREG": _entry(
        "Linear Regression Value",
        "Least-squares regression line value at current bar.",
        "LINEARREG fits a rolling straight line through recent prices and outputs its endpoint.",
        "It can act as a smoother that preserves directional slope information.",
        "LINEARREG_t = Intercept_t + Slope_t*(N-1)",
    ),
    "LINEARREG_ANGLE": _entry(
        "Linear Regression Angle",
        "Slope angle of rolling linear regression line.",
        "This indicator converts regression slope into degrees for easier interpretation.",
        "Steeper positive angles indicate stronger upward drift in the regression fit.",
        "Angle = arctan(LinearRegSlope) * 180/pi",
    ),
    "LINEARREG_INTERCEPT": _entry(
        "Linear Regression Intercept",
        "Intercept term from rolling least-squares fit.",
        "The intercept anchors the regression line and helps reconstruct fitted values.",
        "Combined with slope, it can project expected line values across the window.",
        "Intercept = y_bar - Slope*x_bar (rolling window)",
    ),
    "LINEARREG_SLOPE": _entry(
        "Linear Regression Slope",
        "Slope of rolling least-squares line.",
        "Slope quantifies directional drift per bar over the lookback period.",
        "Positive slope indicates upward trend pressure and negative slope indicates downward drift.",
        "Slope = Cov(x,price)/Var(x) over rolling window",
    ),
    "MA": _entry(
        "Moving Average (Generic)",
        "Configurable moving average type over price.",
        "MA is TA-Lib's generic moving-average wrapper that supports SMA, EMA, WMA and others.",
        "Choosing MA type changes lag and smoothness, so optimize settings per market regime.",
        "MA = selected_matype(price, N)",
    ),
    "MACD": _entry(
        "Moving Average Convergence Divergence",
        "Fast-slow EMA spread with signal and histogram.",
        "MACD combines trend and momentum by comparing short and long EMAs.",
        "Signal-line crossovers and histogram direction are common momentum triggers.",
        "MACD=EMA_fast-EMA_slow; Signal=EMA(MACD,signal); Hist=MACD-Signal",
    ),
    "MACDEXT": _entry(
        "MACD Extended",
        "MACD variant with configurable MA types for each leg.",
        "MACDEXT generalizes MACD by allowing custom moving-average types and periods.",
        "It is useful when you want non-EMA components, such as T3 or WMA signal smoothing.",
        "MACDEXT = MA_fast(price)-MA_slow(price); Signal = MA_signal(MACDEXT)",
    ),
    "MACDFIX": _entry(
        "MACD Fixed 12/26",
        "MACD with fixed 12/26 fast/slow periods.",
        "MACDFIX keeps standard MACD fast and slow periods while letting signal period vary.",
        "This is convenient when you want classic MACD behavior across many assets.",
        "MACDFIX = EMA_12 - EMA_26; Signal = EMA(MACDFIX, signalPeriod)",
    ),
    "MAMA": _entry(
        "MESA Adaptive Moving Average",
        "Adaptive pair of lines: MAMA and FAMA.",
        "MAMA adapts quickly to market phase changes and outputs a companion FAMA line.",
        "Crossovers between MAMA and FAMA are used as adaptive trend-change signals.",
        "MAMA_t = alpha_t*Price_t + (1-alpha_t)*MAMA_(t-1); FAMA = smoother MAMA",
    ),
    "MAX": _entry(
        "Maximum Value",
        "Highest value seen in the lookback window.",
        "MAX returns the rolling highest value, often used for breakout or channel logic.",
        "Price crossing recent MAX can signal renewed upward momentum.",
        "MAX_t = max(Price_(t-N+1) ... Price_t)",
    ),
    "MAXINDEX": _entry(
        "Maximum Index",
        "Index offset of highest value in lookback window.",
        "MAXINDEX identifies where the rolling maximum occurred within the window.",
        "This helps measure recency of highs and can support custom trend aging metrics.",
        "MAXINDEX_t = argmax(Price_(t-N+1) ... Price_t)",
    ),
    "MEDPRICE": _entry(
        "Median Price",
        "Midpoint of high and low for each bar.",
        "MEDPRICE removes open/close noise and focuses on intrabar range center.",
        "It is commonly used as a stable input series for smoothed indicators.",
        "MEDPRICE = (H + L) / 2",
    ),
    "MFI": _entry(
        "Money Flow Index",
        "Volume-weighted momentum oscillator in 0-100 range.",
        "MFI uses typical price and volume to estimate buying versus selling pressure.",
        "High readings can signal overbought conditions, while low readings can signal oversold conditions.",
        "TP=(H+L+C)/3; MFI=100-(100/(1+PositiveMoneyFlow/NegativeMoneyFlow))",
    ),
    "MIDPOINT": _entry(
        "Midpoint",
        "Midpoint between rolling max and min of one series.",
        "MIDPOINT centers the recent value range into a single baseline line.",
        "It is often paired with breakout logic to detect when price leaves its recent center.",
        "MIDPOINT = (MAX(price,N) + MIN(price,N)) / 2",
    ),
    "MIDPRICE": _entry(
        "Midprice",
        "Midpoint between rolling highest high and lowest low.",
        "MIDPRICE defines the center of the recent high-low channel.",
        "Traders compare close to MIDPRICE to judge whether price is in upper or lower half of range.",
        "MIDPRICE = (MAX(high,N) + MIN(low,N)) / 2",
    ),
    "MIN": _entry(
        "Minimum Value",
        "Lowest value seen in the lookback window.",
        "MIN returns the rolling low and is often used for trailing support or stop logic.",
        "Breaks below recent MIN can confirm downside continuation.",
        "MIN_t = min(Price_(t-N+1) ... Price_t)",
    ),
    "MININDEX": _entry(
        "Minimum Index",
        "Index offset of lowest value in lookback window.",
        "MININDEX locates where the rolling minimum occurred in the window.",
        "This can help evaluate whether downside pressure is fresh or stale.",
        "MININDEX_t = argmin(Price_(t-N+1) ... Price_t)",
    ),
    "MINMAX": _entry(
        "Minimum and Maximum",
        "Returns rolling minimum and maximum together.",
        "MINMAX provides channel bounds in one call for faster signal construction.",
        "Many traders use these bounds for breakout and pullback systems.",
        "MINMAX_t = {MIN(price,N), MAX(price,N)}",
    ),
    "MINMAXINDEX": _entry(
        "Minimum and Maximum Index",
        "Index offsets for rolling min and max values.",
        "MINMAXINDEX gives both argmin and argmax positions in the same window.",
        "It is useful for custom structure analysis such as swing sequencing.",
        "MINMAXINDEX_t = {argmin(price,N), argmax(price,N)}",
    ),
    "MINUS_DI": _entry(
        "Minus Directional Indicator",
        "Smoothed bearish directional movement strength.",
        "Minus DI estimates the intensity of downward directional movement.",
        "When -DI is above +DI, many traders treat bearish pressure as dominant.",
        "-DI = 100 * WilderMA(-DM, N) / ATR",
    ),
    "MINUS_DM": _entry(
        "Minus Directional Movement",
        "Raw downward directional movement component.",
        "Minus DM captures down-move magnitude when lows fall more than highs rise.",
        "It feeds into -DI and ADX calculations for trend diagnostics.",
        "-DM = max(L_prev - L, 0) when (L_prev-L) > (H-H_prev) else 0",
    ),
    "MOM": _entry(
        "Momentum",
        "Simple price change over N bars.",
        "MOM measures absolute momentum by subtracting price N periods ago.",
        "Positive values indicate net upward movement; negative values indicate net downward movement.",
        "MOM = Price_t - Price_(t-N)",
    ),
    "NATR": _entry(
        "Normalized Average True Range",
        "ATR expressed as percent of close.",
        "NATR scales volatility by current price so assets with different prices are comparable.",
        "It is useful for volatility-based filters in multi-asset systems.",
        "NATR = 100 * ATR(N) / Close",
    ),
    "OBV": _entry(
        "On-Balance Volume",
        "Cumulative volume added on up closes, subtracted on down closes.",
        "OBV tries to detect volume confirmation ahead of price trends.",
        "Rising OBV during consolidation can hint at stealth accumulation.",
        "OBV_t = OBV_(t-1) + sign(C_t - C_(t-1)) * Volume_t",
    ),
    "PLUS_DI": _entry(
        "Plus Directional Indicator",
        "Smoothed bullish directional movement strength.",
        "Plus DI estimates the intensity of upward directional movement.",
        "When +DI is above -DI, many traders read bullish pressure as dominant.",
        "+DI = 100 * WilderMA(+DM, N) / ATR",
    ),
    "PLUS_DM": _entry(
        "Plus Directional Movement",
        "Raw upward directional movement component.",
        "Plus DM captures up-move magnitude when highs rise more than lows fall.",
        "It feeds into +DI and ADX trend calculations.",
        "+DM = max(H - H_prev, 0) when (H-H_prev) > (L_prev-L) else 0",
    ),
    "PPO": _entry(
        "Percentage Price Oscillator",
        "Fast-slow MA spread as a percentage of slow MA.",
        "PPO is MACD in percent form, making readings comparable across price levels.",
        "Traders use PPO when comparing momentum across different assets.",
        "PPO = 100 * (MA_fast - MA_slow) / MA_slow",
    ),
    "ROC": _entry(
        "Rate of Change",
        "Percent change versus N bars ago.",
        "ROC expresses momentum as percent growth over the lookback period.",
        "Large positive spikes can signal breakout acceleration; deep negatives can signal capitulation.",
        "ROC = 100 * (Price_t - Price_(t-N)) / Price_(t-N)",
    ),
    "ROCP": _entry(
        "Rate of Change Percentage",
        "Decimal percent change versus N bars ago.",
        "ROCP is the fractional form of ROC without multiplying by 100.",
        "Use it when your model expects decimal returns instead of percent points.",
        "ROCP = (Price_t - Price_(t-N)) / Price_(t-N)",
    ),
    "ROCR": _entry(
        "Rate of Change Ratio",
        "Price ratio versus N bars ago.",
        "ROCR returns multiplicative return as a ratio around 1.0.",
        "Values above 1 indicate appreciation; below 1 indicate depreciation over the lookback.",
        "ROCR = Price_t / Price_(t-N)",
    ),
    "ROCR100": _entry(
        "Rate of Change Ratio 100",
        "ROCR scaled by 100.",
        "ROCR100 is ratio momentum rescaled so a flat move equals 100.",
        "It can make dashboard thresholds easier when other indicators are around 0-100.",
        "ROCR100 = 100 * Price_t / Price_(t-N)",
    ),
    "RSI": _entry(
        "Relative Strength Index",
        "0-100 momentum oscillator from average gains and losses.",
        "RSI compares average upward closes to average downward closes over a period.",
        "Common interpretations use overbought/oversold zones and bullish or bearish divergences.",
        "RSI = 100 - (100 / (1 + RS)); RS = AvgGain/AvgLoss",
    ),
    "SAR": _entry(
        "Parabolic SAR",
        "Trailing stop curve that accelerates with trend extension.",
        "Parabolic SAR moves closer to price as a trend continues using an acceleration factor.",
        "A flip of SAR to the opposite side of price can indicate trend reversal.",
        "SAR_t = SAR_(t-1) + AF * (EP - SAR_(t-1))",
    ),
    "SAREXT": _entry(
        "Parabolic SAR Extended",
        "SAR with separate long/short acceleration settings.",
        "SAREXT extends SAR by allowing distinct acceleration and limit parameters for each side.",
        "It is useful when uptrends and downtrends behave differently in your market.",
        "SAREXT uses SAR recursion with configurable AF_init/inc/max for long and short legs",
    ),
    "SMA": _entry(
        "Simple Moving Average",
        "Arithmetic mean of price over N bars.",
        "SMA smooths short-term noise to highlight trend direction and support/resistance zones.",
        "Crossovers between fast and slow SMAs are classic trend-following signals.",
        "SMA = Sum(price, N) / N",
    ),
    "STDDEV": _entry(
        "Standard Deviation",
        "Rolling dispersion of price around its mean.",
        "STDDEV quantifies volatility by measuring spread around the moving average.",
        "Higher values imply larger swings and often larger risk.",
        "STDDEV = sqrt(Variance(price, N))",
    ),
    "STOCH": _entry(
        "Stochastic Oscillator",
        "Compares close to recent high-low range.",
        "Stochastic tracks where the close sits within the lookback trading range.",
        "Crosses of %K and %D near extreme zones are common reversal timing signals.",
        "%K = 100*(C-L_n)/(H_n-L_n); %D = MA(%K, dPeriod)",
    ),
    "STOCHF": _entry(
        "Fast Stochastic",
        "Less-smoothed stochastic %K/%D pair.",
        "STOCHF reacts faster than standard stochastic by using minimal smoothing.",
        "Its speed can catch turns earlier but also increases false signals in noisy markets.",
        "Fast%K = 100*(C-L_n)/(H_n-L_n); Fast%D = MA(Fast%K, dPeriod)",
    ),
    "STOCHRSI": _entry(
        "Stochastic RSI",
        "Stochastic calculation applied to RSI values.",
        "StochRSI amplifies RSI sensitivity by normalizing RSI inside its own recent range.",
        "It can provide earlier momentum turns, but often needs confirmation to reduce whipsaw.",
        "StochRSI = (RSI - min(RSI,N)) / (max(RSI,N) - min(RSI,N))",
    ),
    "SUM": _entry(
        "Rolling Sum",
        "Sum of values over the lookback window.",
        "SUM accumulates recent values and is useful for custom indicator construction.",
        "For example, it can build volume pressure or rolling payoff totals.",
        "SUM_t = sum(Price_(t-N+1) ... Price_t)",
    ),
    "T3": _entry(
        "Triple Exponential T3",
        "Very smooth moving average with low lag tuning.",
        "T3 applies multiple EMA passes with a volume factor to balance smoothness and responsiveness.",
        "It is often preferred when traders want cleaner trend lines than EMA without excessive delay.",
        "T3 = Tillson T3 recursion using EMA cascades and volume factor vFactor",
    ),
    "TEMA": _entry(
        "Triple Exponential Moving Average",
        "Lag-reduced average built from three EMA layers.",
        "TEMA improves responsiveness by combining first, second, and third EMA levels.",
        "It follows trend changes quickly but can overreact in choppy ranges.",
        "TEMA = 3*EMA1 - 3*EMA2 + EMA3",
    ),
    "TRANGE": _entry(
        "True Range",
        "Single-bar true range including gap risk.",
        "TRANGE captures the largest of intrabar range and gap-to-previous-close moves.",
        "It is the core volatility input used by ATR and related risk tools.",
        "TR = max(H-L, |H-C_prev|, |L-C_prev|)",
    ),
    "TRIMA": _entry(
        "Triangular Moving Average",
        "Double-smoothed SMA with triangular weights.",
        "TRIMA applies stronger weighting to middle observations for extra smoothness.",
        "It is stable for trend filtering but slower to react to abrupt reversals.",
        "TRIMA = SMA(SMA(price, ceil((N+1)/2)), floor((N+1)/2))",
    ),
    "TRIX": _entry(
        "TRIX Oscillator",
        "Rate of change of triple-smoothed EMA.",
        "TRIX filters noise by using a triple EMA before computing momentum change.",
        "Zero-line crosses and signal-line crosses are common trend-momentum cues.",
        "TRIX = 100 * (EMA3_t - EMA3_(t-1)) / EMA3_(t-1)",
    ),
    "TSF": _entry(
        "Time Series Forecast",
        "Linear-regression forecast of current-bar value.",
        "TSF projects the fitted regression line forward to estimate expected value.",
        "It is often used as a dynamic baseline for trend continuation tests.",
        "TSF_t = Intercept_t + Slope_t*(N-1)",
    ),
    "TYPPRICE": _entry(
        "Typical Price",
        "Average of high, low, and close.",
        "Typical price is a balanced per-bar price used in indicators like CCI and MFI.",
        "It reduces open-price noise and focuses on where most trading occurred.",
        "TYPPRICE = (H + L + C) / 3",
    ),
    "ULTOSC": _entry(
        "Ultimate Oscillator",
        "Weighted momentum over short, medium, and long windows.",
        "Ultimate Oscillator blends multiple horizons to reduce false divergence signals.",
        "It is often used to confirm reversals when momentum improves across all windows.",
        "UO = 100 * (4*Avg7(BP/TR) + 2*Avg14(BP/TR) + Avg28(BP/TR)) / 7",
    ),
    "VAR": _entry(
        "Variance",
        "Rolling variance of the input series.",
        "Variance measures squared dispersion around the rolling mean.",
        "It is useful in volatility models and risk-adjusted position sizing.",
        "VAR = mean((price - mean(price,N))^2)",
    ),
    "WCLPRICE": _entry(
        "Weighted Close Price",
        "Close-weighted average of high, low, and close.",
        "WCLPRICE emphasizes the close while still accounting for bar extremes.",
        "Many traders use it as a smoother input than raw close alone.",
        "WCLPRICE = (H + L + 2*C) / 4",
    ),
    "WILLR": _entry(
        "Williams %R",
        "Momentum oscillator of close within recent high-low range.",
        "Williams %R is an inverted stochastic style oscillator typically shown from -100 to 0.",
        "Readings near -100 imply closes near range lows, while near 0 imply closes near highs.",
        "%R = -100 * (H_n - C) / (H_n - L_n)",
    ),
    "WMA": _entry(
        "Weighted Moving Average",
        "Moving average with linearly increasing recent weights.",
        "WMA gives the newest bars the largest weights and oldest bars the smallest.",
        "It reacts faster than SMA while remaining simpler than adaptive averages.",
        "WMA = sum(i*Price_i, i=1..N) / sum(i, i=1..N)",
    ),
}


_CDL: dict[str, dict[str, str]] = {
    "CDL2CROWS": _cdl_entry(
        "Two Crows",
        "a long white candle followed by two black candles gapping up then closing lower",
        "a bearish reversal after an uptrend",
    ),
    "CDL3BLACKCROWS": _cdl_entry(
        "Three Black Crows",
        "three consecutive long bearish candles closing near their lows",
        "strong bearish reversal pressure",
    ),
    "CDL3INSIDE": _cdl_entry(
        "Three Inside Up/Down",
        "a harami pair followed by a confirmation candle in the opposite direction",
        "a potential trend reversal",
    ),
    "CDL3LINESTRIKE": _cdl_entry(
        "Three-Line Strike",
        "three trend candles then one large opposite candle engulfing the prior three",
        "a potential exhaustion reversal",
    ),
    "CDL3STARSINSOUTH": _cdl_entry(
        "Three Stars in the South",
        "three shrinking bearish candles with reduced downside follow-through",
        "a bullish reversal setup",
    ),
    "CDL3WHITESOLDIERS": _cdl_entry(
        "Three White Soldiers",
        "three strong bullish candles with progressively higher closes",
        "a bullish reversal or continuation",
    ),
    "CDLABANDONEDBABY": _cdl_entry(
        "Abandoned Baby",
        "a [[CDLDOJI|doji]] gapped away between two opposite candles",
        "a high-conviction reversal signal",
    ),
    "CDLADVANCEBLOCK": _cdl_entry(
        "Advance Block",
        "three rising bullish candles with weakening bodies and upper shadows",
        "a bearish warning after an up move",
    ),
    "CDLBELTHOLD": _cdl_entry(
        "Belt Hold",
        "a long candle opening at one extreme and closing strongly the other way",
        "a possible reversal in the candle direction",
    ),
    "CDLBREAKAWAY": _cdl_entry(
        "Breakaway",
        "five-candle sequence with a gap that eventually gets retraced",
        "a reversal from the prior trend",
    ),
    "CDLCLOSINGMARUBOZU": _cdl_entry(
        "Closing Marubozu",
        "a long candle that closes at its high or low with little opposite wick",
        "strong directional commitment",
    ),
    "CDLCONCEALBABYSWALL": _cdl_entry(
        "Concealing Baby Swallow",
        "a rare four-candle bearish sequence ending with a bullish [[CDLENGULFING|engulfing]] concealment",
        "a bullish reversal from downside exhaustion",
    ),
    "CDLCOUNTERATTACK": _cdl_entry(
        "Counterattack",
        "two opposite long candles that close at nearly the same level",
        "a possible reversal at support or resistance",
    ),
    "CDLDARKCLOUDCOVER": _cdl_entry(
        "Dark Cloud Cover",
        "a bullish candle followed by a bearish candle closing deep into the prior body",
        "a bearish reversal signal",
    ),
    "CDLDOJI": _cdl_entry(
        "Doji",
        "open and close are nearly equal with visible intrabar range",
        "market indecision that can precede reversal",
    ),
    "CDLDOJISTAR": _cdl_entry(
        "Doji Star",
        "a [[CDLDOJI|doji]] that gaps away from the prior real body",
        "an early reversal warning",
    ),
    "CDLDRAGONFLYDOJI": _cdl_entry(
        "Dragonfly Doji",
        "[[CDLDOJI|doji]] with long lower shadow and little upper shadow",
        "bullish rejection of lower prices",
    ),
    "CDLENGULFING": _cdl_entry(
        "Engulfing",
        "a real body that fully engulfs the previous real body",
        "a strong reversal toward the engulfing candle direction",
    ),
    "CDLEVENINGDOJISTAR": _cdl_entry(
        "Evening Doji Star",
        "bullish candle, gapped [[CDLDOJI|doji]], then bearish confirmation candle",
        "a bearish top reversal",
    ),
    "CDLEVENINGSTAR": _cdl_entry(
        "Evening Star",
        "strong bullish candle, small indecision candle, then bearish follow-through",
        "a bearish reversal pattern related to [[CDLMORNINGSTAR|Morning Star]]",
    ),
    "CDLGAPSIDESIDEWHITE": _cdl_entry(
        "Up/Down-gap Side-by-side White Lines",
        "two similar white candles side by side after a gap",
        "continuation in the direction of the gap",
    ),
    "CDLGRAVESTONEDOJI": _cdl_entry(
        "Gravestone Doji",
        "[[CDLDOJI|doji]] with long upper shadow and little lower shadow",
        "bearish rejection of higher prices",
    ),
    "CDLHAMMER": _cdl_entry(
        "Hammer",
        "small real body near top with long lower shadow after a decline",
        "a bullish reversal attempt",
    ),
    "CDLHANGINGMAN": _cdl_entry(
        "Hanging Man",
        "[[CDLHAMMER|hammer]]-shaped candle appearing after an advance",
        "a bearish reversal warning",
    ),
    "CDLHARAMI": _cdl_entry(
        "Harami",
        "small real body contained inside the previous large real body",
        "trend slowdown and possible reversal",
    ),
    "CDLHARAMICROSS": _cdl_entry(
        "Harami Cross",
        "a [[CDLDOJI|doji]] contained inside the previous large real body",
        "a stronger reversal warning than regular [[CDLHARAMI|harami]]",
    ),
    "CDLHIGHWAVE": _cdl_entry(
        "High-Wave Candle",
        "small body with long upper and lower shadows",
        "high indecision and potential turning point",
    ),
    "CDLHIKKAKE": _cdl_entry(
        "Hikkake",
        "inside bar trap followed by breakout failure",
        "short-term reversal after trapped breakout traders",
    ),
    "CDLHIKKAKEMOD": _cdl_entry(
        "Modified Hikkake",
        "variant hikkake sequence with stricter inside and confirmation structure",
        "reversal after failed directional break",
    ),
    "CDLHOMINGPIGEON": _cdl_entry(
        "Homing Pigeon",
        "two bearish candles where the second body sits inside the first",
        "a bullish reversal hint in downtrends",
    ),
    "CDLIDENTICAL3CROWS": _cdl_entry(
        "Identical Three Crows",
        "three bearish candles with similar opens and steady lower closes",
        "a strong bearish reversal formation",
    ),
    "CDLINNECK": _cdl_entry(
        "In-Neck",
        "downtrend gap-down candle followed by small bullish close near prior low",
        "a bearish continuation pattern",
    ),
    "CDLINVERTEDHAMMER": _cdl_entry(
        "Inverted Hammer",
        "small body near low with long upper shadow after decline",
        "a bullish reversal candidate pending confirmation",
    ),
    "CDLKICKING": _cdl_entry(
        "Kicking",
        "opposite [[CDLMARUBOZU|marubozu]] candles separated by a gap",
        "a strong reversal signal",
    ),
    "CDLKICKINGBYLENGTH": _cdl_entry(
        "Kicking (by Longer Marubozu)",
        "[[CDLKICKING|kicking]] pattern where direction follows the longer [[CDLMARUBOZU|marubozu]] candle",
        "a forceful reversal toward dominant candle",
    ),
    "CDLLADDERBOTTOM": _cdl_entry(
        "Ladder Bottom",
        "extended decline with small recovery candle then bullish confirmation",
        "a bullish reversal structure",
    ),
    "CDLLONGLEGGEDDOJI": _cdl_entry(
        "Long Legged Doji",
        "[[CDLDOJI|doji]] with very long upper and lower shadows",
        "extreme indecision that can precede reversal",
    ),
    "CDLLONGLINE": _cdl_entry(
        "Long Line Candle",
        "a candle with an unusually long real body",
        "strong directional conviction in candle direction",
    ),
    "CDLMARUBOZU": _cdl_entry(
        "Marubozu",
        "long body candle with little or no shadows",
        "strong continuation or reversal momentum",
    ),
    "CDLMATCHINGLOW": _cdl_entry(
        "Matching Low",
        "two bearish candles with nearly equal lows",
        "a bullish reversal support clue",
    ),
    "CDLMATHOLD": _cdl_entry(
        "Mat Hold",
        "strong trend candle, brief pullback cluster, then trend resumption candle",
        "a continuation pattern",
    ),
    "CDLMORNINGDOJISTAR": _cdl_entry(
        "Morning Doji Star",
        "bearish candle, gapped [[CDLDOJI|doji]], then bullish confirmation candle",
        "a bullish bottom reversal",
    ),
    "CDLMORNINGSTAR": _cdl_entry(
        "Morning Star",
        "strong bearish candle, small base candle, then bullish follow-through",
        "a bullish reversal pattern related to [[CDLEVENINGSTAR|Evening Star]]",
    ),
    "CDLONNECK": _cdl_entry(
        "On-Neck",
        "downtrend gap-down candle followed by small bullish close at prior low",
        "a bearish continuation signal",
    ),
    "CDLPIERCING": _cdl_entry(
        "Piercing Pattern",
        "bearish candle then bullish candle closing above midpoint of prior body",
        "a bullish reversal setup",
    ),
    "CDLRICKSHAWMAN": _cdl_entry(
        "Rickshaw Man",
        "[[CDLDOJI|doji]]-like candle with very long upper and lower shadows",
        "strong indecision and possible reversal",
    ),
    "CDLRISEFALL3METHODS": _cdl_entry(
        "Rising/Falling Three Methods",
        "long trend candle, three small counter candles, then trend continuation candle",
        "continuation of the original trend",
    ),
    "CDLSEPARATINGLINES": _cdl_entry(
        "Separating Lines",
        "opposite candles sharing similar open in an existing trend",
        "continuation in the prevailing trend",
    ),
    "CDLSHOOTINGSTAR": _cdl_entry(
        "Shooting Star",
        "small body near low with long upper shadow after an advance",
        "a bearish reversal warning",
    ),
    "CDLSHORTLINE": _cdl_entry(
        "Short Line Candle",
        "candle with unusually short real body",
        "reduced conviction and potential pause",
    ),
    "CDLSPINNINGTOP": _cdl_entry(
        "Spinning Top",
        "small real body with upper and lower shadows",
        "indecision that may precede reversal",
    ),
    "CDLSTALLEDPATTERN": _cdl_entry(
        "Stalled Pattern",
        "three-candle bullish advance ending with weakening final candle",
        "a bearish warning near trend exhaustion",
    ),
    "CDLSTICKSANDWICH": _cdl_entry(
        "Stick Sandwich",
        "three candles where first and third closes match around a middle opposite candle",
        "a bullish reversal clue",
    ),
    "CDLTAKURI": _cdl_entry(
        "Takuri",
        "[[CDLDRAGONFLYDOJI|dragonfly doji]]-like candle with very long lower shadow after decline",
        "bullish rejection and possible reversal",
    ),
    "CDLTASUKIGAP": _cdl_entry(
        "Tasuki Gap",
        "gap continuation pattern interrupted by opposite candle that does not fill the gap",
        "trend continuation in gap direction",
    ),
    "CDLTHRUSTING": _cdl_entry(
        "Thrusting Pattern",
        "downtrend candle then bullish candle closing into but not above prior midpoint",
        "usually bearish continuation",
    ),
    "CDLTRISTAR": _cdl_entry(
        "Tristar",
        "three consecutive [[CDLDOJI|doji]] candles with gap structure",
        "a notable reversal signal",
    ),
    "CDLUNIQUE3RIVER": _cdl_entry(
        "Unique Three River",
        "bearish candle, [[CDLHAMMER|hammer]]-like candle, then small confirmation candle",
        "a bullish reversal candidate",
    ),
    "CDLUPSIDEGAP2CROWS": _cdl_entry(
        "Upside Gap Two Crows",
        "uptrend gap up followed by two bearish candles",
        "a bearish reversal warning",
    ),
    "CDLXSIDEGAP3METHODS": _cdl_entry(
        "Upside/Downside Gap Three Methods",
        "three-candle gap pattern with middle consolidation and final continuation",
        "continuation in the original gap direction",
    ),
}


GLOSSARY_ENTRIES: dict[str, dict[str, str]] = {**_NON_CDL, **_CDL}

_expected = set(TA_FUNCTION_NAMES)
_actual = set(GLOSSARY_ENTRIES)
if _actual != _expected:
    missing = sorted(_expected - _actual)
    extra = sorted(_actual - _expected)
    raise ValueError(f"GLOSSARY_ENTRIES mismatch. missing={missing}, extra={extra}")
