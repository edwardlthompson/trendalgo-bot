"""TA-Lib function categories (aligned with https://ta-lib.org/function.html groups)."""

from __future__ import annotations

from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator

CATEGORY_ORDER: tuple[str, ...] = (
    "Overlap Studies",
    "Momentum Indicators",
    "Volume Indicators",
    "Volatility Indicators",
    "Fibonacci & Levels",
    "Pattern Recognition",
    "Cycle Indicators",
    "Price Transform",
    "Statistic Functions",
    "Math Operators",
    "Math Transform",
    "Extended Indicators",
)

_OVERLAP = {
    "BBANDS", "DEMA", "EMA", "HT_TRENDLINE", "KAMA", "MA", "MAMA", "MIDPOINT", "MIDPRICE",
    "SAR", "SAREXT", "SMA", "T3", "TEMA", "TRIMA", "WMA",
}
_MOMENTUM = {
    "ADX", "ADXR", "APO", "AROON", "AROONOSC", "BOP", "CCI", "CMO", "DX", "MACD", "MACDEXT",
    "MACDFIX", "MFI", "MINUS_DI", "MINUS_DM", "MOM", "PLUS_DI", "PLUS_DM", "PPO", "ROC", "ROCP",
    "ROCR", "ROCR100", "RSI", "STOCH", "STOCHF", "STOCHRSI", "TRIX", "ULTOSC", "WILLR",
}
_VOLUME = {"AD", "ADOSC", "OBV"}
_VOLATILITY = {"ATR", "NATR", "TRANGE"}
_CYCLE = {"HT_DCPERIOD", "HT_DCPHASE", "HT_PHASOR", "HT_SINE", "HT_TRENDMODE"}
_PRICE = {"AVGPRICE", "MEDPRICE", "TYPPRICE", "WCLPRICE"}
_STATS = {"BETA", "CORREL", "LINEARREG", "LINEARREG_ANGLE", "LINEARREG_INTERCEPT", "LINEARREG_SLOPE",
          "STDDEV", "TSF", "VAR", "MAX", "MAXINDEX", "MIN", "MININDEX", "MINMAX", "MINMAXINDEX", "SUM"}
_MATH_OP = {"ADD", "DIV", "MAX", "MIN", "MULT", "SUB", "SUM"}
_MATH_TR = {"ACOS", "ASIN", "ATAN", "CEIL", "COS", "COSH", "EXP", "FLOOR", "LN", "LOG10", "SIN",
              "SINH", "SQRT", "TAN", "TANH"}


_FIBONACCI = set(CUSTOM_TA_NAMES)
_PTA_OVERLAP = {
    "ALMA", "DONCHIAN", "FWMA", "HA", "HILO", "HL2", "HLC3", "HMA", "HWC", "HWMA", "ICHIMOKU",
    "JMA", "KC", "OHLC4", "PSAR", "PWMA", "RAINBOW", "RMA", "SINWMA", "SUPERTREND", "SWMA",
    "VIDYA", "VWAP", "VWMA", "WCP", "ZLMA",
}
_PTA_MOMENTUM = {
    "AO", "BIAS", "BRAR", "CFO", "CG", "COPPOCK", "CTI", "ER", "FISHER", "INERTIA", "KDJ", "KST",
    "LRSI", "PGO", "QQE", "RSX", "RVGI", "RVI", "SLOPE", "SMI", "SQUEEZE", "SQUEEZE_PRO", "STC",
    "TD_SEQ", "TSI", "TTM_TREND", "UO", "VORTEX",
}
_PTA_VOLUME = {"CMF", "EFI", "EOM", "KVO", "NVI", "PVI", "PVT", "PVO", "VFI", "VP", "VWAP", "VWMA"}
_PTA_MATH = {
    "ACOS", "ASIN", "ATAN", "CEIL", "COS", "COSH", "EXP", "FLOOR", "LN", "LOG10", "SIN", "SINH", "SQRT", "TAN",
    "TANH", "ADD", "DIV", "MULT", "SUB", "LOG_RETURN", "PERCENT_RETURN",
}
_PTA_STATS = {
    "ENTROPY", "KURTOSIS", "MAD", "MEDIAN", "SKEW", "STDERR", "VARIANCE", "ZSCORE", "QUANTILE", "TODEG", "TORAD",
    "ROLLING_MAX", "ROLLING_MIN", "ROLLING_SUM", "NPABS", "NPROUND", "TRUNC",
}
_PTA_PRICE = {"HL2", "HLC3", "OHLC4", "WCP", "PDIST", "WCP"}
_PTA_CYCLE = {"EBSW", "MSW", "REFLEX", "SMC_SWEEP"}


_PTA_VOLATILITY = {
    "ABERRATION", "ACCBANDS", "CHOP", "HVOL", "MASSI", "THERMO", "UI", "VHF", "TRUE_RANGE", "DECAY", "EDECAY", "DRAWDOWN",
}


def ta_category(name: str) -> str:
    upper = name.upper()
    if upper in _FIBONACCI:
        return "Fibonacci & Levels"
    if is_pandas_ta_indicator(upper):
        if upper in _PTA_OVERLAP:
            return "Overlap Studies"
        if upper in _PTA_MOMENTUM:
            return "Momentum Indicators"
        if upper in _PTA_VOLUME:
            return "Volume Indicators"
        if upper in _PTA_VOLATILITY:
            return "Volatility Indicators"
        if upper in _PTA_CYCLE:
            return "Cycle Indicators"
        if upper in _PTA_PRICE:
            return "Price Transform"
        if upper in _PTA_STATS:
            return "Statistic Functions"
        if upper in _PTA_MATH:
            if upper in {"ACOS", "ASIN", "ATAN", "CEIL", "COS", "COSH", "EXP", "FLOOR", "LN", "LOG10", "SIN", "SINH", "SQRT", "TAN", "TANH"}:
                return "Math Transform"
            return "Math Operators"
        return "Extended Indicators"
    if name.startswith("CDL"):
        return "Pattern Recognition"
    if name in _OVERLAP:
        return "Overlap Studies"
    if name in _MOMENTUM:
        return "Momentum Indicators"
    if name in _VOLUME:
        return "Volume Indicators"
    if name in _VOLATILITY:
        return "Volatility Indicators"
    if name in _CYCLE:
        return "Cycle Indicators"
    if name in _PRICE:
        return "Price Transform"
    if name in _STATS:
        return "Statistic Functions"
    if name in _MATH_OP:
        return "Math Operators"
    if name in _MATH_TR:
        return "Math Transform"
    return "Momentum Indicators"


def build_ta_library() -> list[dict[str, str]]:
    items = [{"id": name, "name": name, "category": ta_category(name)} for name in all_ta_names()]
    items.sort(key=lambda x: (CATEGORY_ORDER.index(x["category"]) if x["category"] in CATEGORY_ORDER else 99, x["name"]))
    return items
