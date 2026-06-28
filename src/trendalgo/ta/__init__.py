"""TA-Lib catalog and optional native bindings — see https://ta-lib.org/functions/."""

from trendalgo.ta.catalog import TA_FUNCTION_NAMES, all_ta_count, all_ta_names, ta_function_count
from trendalgo.ta.engine import talib_available
from trendalgo.ta.pandas_ta_catalog import pandas_ta_available, pandas_ta_function_count
from trendalgo.ta.sweep import run_ta_sweep

__all__ = [
    "TA_FUNCTION_NAMES",
    "all_ta_count",
    "all_ta_names",
    "pandas_ta_available",
    "pandas_ta_function_count",
    "run_ta_sweep",
    "ta_function_count",
    "talib_available",
]
