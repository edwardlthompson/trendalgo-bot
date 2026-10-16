"""Signal-kind classification and oscillator levels (Investopedia-aligned)."""

from __future__ import annotations

from typing import Any

from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.pandas_ta_catalog import is_pandas_ta_indicator

# Close crossing the indicator line.
PRICE_CROSS_IDS: frozenset[str] = frozenset(
    {
        "SMA",
        "EMA",
        "DEMA",
        "TEMA",
        "WMA",
        "KAMA",
        "T3",
        "TRIMA",
        "BBANDS",
        "MIDPOINT",
        "MIDPRICE",
        "HT_TRENDLINE",
        "SAR",
        "SAREXT",
        "FIB_RETRACE",
        "FIB_EXT",
        "SUPERTREND",
        "VWAP",
        "VWMA",
        "HMA",
        "ZLMA",
        "ALMA",
        "FWMA",
        "PWMA",
        "SWMA",
        "SINWMA",
        "HWMA",
        "VIDYA",
        "RMA",
        "JMA",
        "DONCHIAN",
        "KC",
        "ACCBANDS",
        "HILO",
        "HWC",
        "ICHIMOKU",
        "PSAR",
        "HL2",
        "HLC3",
        "OHLC4",
        "WCP",
        "AVGPRICE",
        "MEDPRICE",
        "TYPPRICE",
        "WCLPRICE",
    }
)

# True bounded oscillators (0–100 or documented zones).
BOUNDED_OSC_IDS: frozenset[str] = frozenset(
    {
        "RSI",
        "MFI",
        "CMO",
        "CCI",
        "WILLR",
        "STOCHRSI",
        "ULTOSC",
        "STOCH",
        "STOCHF",
        "KDJ",
        "QQE",
        "RSX",
        "LRSI",
        "UO",
        "STC",
        "SMI",
        "RVI",
        "RVGI",
        "FISHER",
        "CTI",
    }
)

# Math / transform / always-positive helpers — not tradable as standalone strategies.
MATH_SKIP_IDS: frozenset[str] = frozenset(
    {
        "ADD",
        "DIV",
        "MAX",
        "MIN",
        "MULT",
        "SUB",
        "SUM",
        "ACOS",
        "ASIN",
        "ATAN",
        "CEIL",
        "COS",
        "COSH",
        "EXP",
        "FLOOR",
        "LN",
        "LOG10",
        "SIN",
        "SINH",
        "SQRT",
        "TAN",
        "TANH",
        "MAXINDEX",
        "MININDEX",
        "MINMAX",
        "MINMAXINDEX",
        # Volatility / stats — not entry signals by themselves
        "ATR",
        "NATR",
        "TRANGE",
        "STDDEV",
        "VAR",
        "BETA",
        "CORREL",
        "LINEARREG",
        "LINEARREG_ANGLE",
        "LINEARREG_INTERCEPT",
        "LINEARREG_SLOPE",
        "TSF",
        "PLUS_DM",
        "MINUS_DM",
        "HT_DCPERIOD",
        "HT_DCPHASE",
        "HT_PHASOR",
        "HT_SINE",
        "HT_TRENDMODE",
        # pandas-ta comparison / utility helpers
        "ABOVE",
        "ABOVE_VALUE",
        "BELOW",
        "BELOW_VALUE",
        "CROSS",
        "CROSSANY",
        "CROSSOVER",
        "CROSS_VALUE",
        "HA",
        "LAG",
        "LONG_RUN",
        "SHORT_RUN",
        "PERCENT_RETURN",
        "LOG_RETURN",
        "DRAWDOWN",
        "ENTROPY",
        "KURTOSIS",
        "SKEW",
        "MAD",
        "MEDIAN",
        "ZSCORE",
        "VHFC",
        "LINREG",
        "LINREGINTERCEPT",
        "LINREGSLOPE",
        "ROCR",  # always-positive price ratio — not a zero-cross oscillator
        "ROCR100",
        "ABERRATION",
        "AVOLUME",
        "BRAR",
        "CE",
        "CHOP",
        "CKSP",
        "CPR",
        "DECAY",
        "EDECAY",
        "HVOL",
        "MARKETFI",
        "MASSI",
        "MAVP",
        "MCGD",
        "MD",
        "MMAR",
        "NPABS",
        "NPROUND",
        "PDIST",
        "PMAX",
        "PVOL",
        "PVR",
        "QUANTILE",
        "RAINBOW",
        "ROLLING_MAX",
        "ROLLING_MIN",
        "ROLLING_SUM",
    }
)

# Investopedia DMI: +DI crosses above −DI (ADX/DX are strength filters, not zero-cross).
DI_CROSS_IDS: frozenset[str] = frozenset({"ADX", "ADXR", "DX", "PLUS_DI", "MINUS_DI", "DM"})

MACD_IDS: frozenset[str] = frozenset({"MACD", "MACDEXT", "MACDFIX"})
MACD_LIKE_IDS: frozenset[str] = frozenset({"MACD", "MACDEXT", "MACDFIX", "PVO", "VWMACD", "MAMA"})
STOCH_IDS: frozenset[str] = frozenset({"STOCH", "STOCHF"})
ZERO_CROSS_IDS: frozenset[str] = frozenset(
    {
        "APO",
        "PPO",
        "ROC",
        "MOM",
        "ROCP",
        "TRIX",
        "AO",
        "COPPOCK",
        "KST",
        "EOM",
        "EFI",
        "CMF",
        "VFI",
        "PVI",
        "NVI",
        "SQUEEZE",
        "SQUEEZE_PRO",
        "VORTEX",
        "AD",
        "ADOSC",
        "OBV",
        "BOP",
        "AROONOSC",
        "AROON",
        "TSI",
        "CFO",
        "CG",
        "ER",
        "INERTIA",
        "PGO",
        "PSL",
        "TD_SEQ",
        "VHF",
        "WTO",
        "SLOPE",
    }
)
MA_CROSS_IDS: frozenset[str] = frozenset(
    {"SMA", "EMA", "DEMA", "TEMA", "WMA", "KAMA", "T3", "TRIMA", "HMA", "VWMA"}
)

# entry_level / exit_level for bounded_reversal (cross up / cross down).
OSC_LEVELS: dict[str, tuple[float, float]] = {
    "RSI": (30.0, 70.0),
    "MFI": (20.0, 80.0),
    "CMO": (-50.0, 50.0),
    "CCI": (-100.0, 100.0),
    "WILLR": (-80.0, -20.0),  # Williams %R ∈ [-100, 0]
    "STOCHRSI": (20.0, 80.0),
    "ULTOSC": (30.0, 70.0),
    "UO": (30.0, 70.0),
    "STOCH": (20.0, 80.0),
    "STOCHF": (20.0, 80.0),
    "KDJ": (20.0, 80.0),
    "QQE": (30.0, 70.0),
    "RSX": (30.0, 70.0),
    "LRSI": (30.0, 70.0),
    "STC": (25.0, 75.0),
    "SMI": (-40.0, 40.0),
    "RVI": (30.0, 70.0),
    "RVGI": (30.0, 70.0),
    "FISHER": (-1.5, 1.5),
    "CTI": (-0.5, 0.5),
}


def signal_kind(strategy_id: str) -> str:
    upper = strategy_id.upper()
    if upper.startswith("CDL"):
        return "cdl_pattern"
    if upper in MATH_SKIP_IDS:
        return "math_skip"
    if upper in DI_CROSS_IDS:
        return "di_cross"
    if upper in MACD_LIKE_IDS:
        return "macd_cross"
    if upper in STOCH_IDS:
        return "stoch_cross"
    if upper in MA_CROSS_IDS:
        return "ma_cross"
    if upper in PRICE_CROSS_IDS:
        return "price_cross"
    if upper in BOUNDED_OSC_IDS:
        return "bounded_reversal"
    if upper in ZERO_CROSS_IDS:
        return "zero_cross"
    if upper in CUSTOM_TA_NAMES or is_pandas_ta_indicator(upper):
        # Unknown pandas-ta: try zero-cross once; helpers should be listed in MATH_SKIP.
        return "zero_cross"
    # Leftover TA-Lib / unknown: prefer price_cross over bogus RSI-style levels.
    return "price_cross"


def oscillator_levels(strategy_id: str) -> tuple[float, float]:
    upper = strategy_id.upper()
    return OSC_LEVELS.get(upper, (30.0, 70.0))


def apply_kind_defaults(preset: dict[str, Any], *, kind: str, upper: str) -> dict[str, Any]:
    """Mutate preset with kind-specific defaults; return same dict."""
    if kind == "ma_cross":
        preset.setdefault("fast", int(preset.get("fast", 10)))
        preset.setdefault("slow", int(preset.get("slow", 30)))
    if kind in {"bounded_reversal", "zero_cross", "di_cross"}:
        preset.setdefault("timeperiod", int(preset.get("timeperiod", preset.get("length", 14))))
    if kind == "bounded_reversal":
        entry, exit_ = oscillator_levels(upper)
        preset.setdefault("entry_level", entry)
        preset.setdefault("exit_level", exit_)
    return preset
