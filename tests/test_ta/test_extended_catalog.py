"""Extended TA catalog and pandas-ta-classic coverage."""

from trendalgo.ta.catalog import all_ta_count, all_ta_names, ta_function_count
from trendalgo.ta.extended_catalog import CUSTOM_TA_NAMES
from trendalgo.ta.pandas_ta_catalog import pandas_ta_function_count
from trendalgo.ta.pandas_ta_names_data import PANDAS_TA_FUNCTION_NAMES


def test_all_ta_names_include_pandas_ta_and_custom() -> None:
    assert all_ta_count() == ta_function_count() + pandas_ta_function_count() + len(CUSTOM_TA_NAMES)
    assert "FIB_RETRACE" in all_ta_names()
    assert "SUPERTREND" in all_ta_names()
    assert "RSI" in all_ta_names()
    assert len(PANDAS_TA_FUNCTION_NAMES) >= 160
