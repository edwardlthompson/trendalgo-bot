"""pandas-ta-classic indicator catalog (community FOSS fork, 168 extras beyond TA-Lib)."""

from __future__ import annotations

from trendalgo.ta.pandas_ta_names_data import PANDAS_TA_FUNCTION_NAMES


def pandas_ta_function_count() -> int:
    return len(PANDAS_TA_FUNCTION_NAMES)


def pandas_ta_available() -> bool:
    try:
        import pandas_ta_classic  # noqa: F401

        return True
    except ImportError:
        return False


def id_to_pandas_ta_slug(indicator_id: str) -> str:
    """Map catalog ID (e.g. SUPERTREND, CDL_DOJI) to pandas-ta slug."""
    return indicator_id.lower()


def is_pandas_ta_indicator(indicator_id: str) -> bool:
    return indicator_id.upper() in PANDAS_TA_FUNCTION_NAMES
