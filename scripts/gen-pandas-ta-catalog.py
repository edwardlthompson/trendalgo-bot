#!/usr/bin/env python3
"""Emit frozen pandas-ta-classic indicator names for offline/tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT_PY = ROOT / "src" / "trendalgo" / "ta" / "pandas_ta_names_data.py"
OUT_JSON = ROOT / "examples" / "web" / "public" / "data" / "ta-library-extra.json"

TALIB_UPPER = {
    "AD",
    "ADOSC",
    "ADX",
    "ADXR",
    "APO",
    "AROON",
    "AROONOSC",
    "ATR",
    "AVGPRICE",
    "BBANDS",
    "BETA",
    "BOP",
    "CCI",
    "CDL2CROWS",
    "CDL3BLACKCROWS",
    "CDL3INSIDE",
    "CDL3LINESTRIKE",
    "CDL3STARSINSOUTH",
    "CDL3WHITESOLDIERS",
    "CDLABANDONEDBABY",
    "CDLADVANCEBLOCK",
    "CDLBELTHOLD",
    "CDLBREAKAWAY",
    "CDLCLOSINGMARUBOZU",
    "CDLCONCEALBABYSWALL",
    "CDLCOUNTERATTACK",
    "CDLDARKCLOUDCOVER",
    "CDLDOJI",
    "CDLDOJISTAR",
    "CDLDRAGONFLYDOJI",
    "CDLENGULFING",
    "CDLEVENINGDOJISTAR",
    "CDLEVENINGSTAR",
    "CDLGAPSIDESIDEWHITE",
    "CDLGRAVESTONEDOJI",
    "CDLHAMMER",
    "CDLHANGINGMAN",
    "CDLHARAMI",
    "CDLHARAMICROSS",
    "CDLHIGHWAVE",
    "CDLHIKKAKE",
    "CDLHIKKAKEMOD",
    "CDLHOMINGPIGEON",
    "CDLIDENTICAL3CROWS",
    "CDLINNECK",
    "CDLINVERTEDHAMMER",
    "CDLKICKING",
    "CDLKICKINGBYLENGTH",
    "CDLLADDERBOTTOM",
    "CDLLONGLEGGEDDOJI",
    "CDLLONGLINE",
    "CDLMARUBOZU",
    "CDLMATCHINGLOW",
    "CDLMATHOLD",
    "CDLMORNINGDOJISTAR",
    "CDLMORNINGSTAR",
    "CDLONNECK",
    "CDLPIERCING",
    "CDLRICKSHAWMAN",
    "CDLRISEFALL3METHODS",
    "CDLSEPARATINGLINES",
    "CDLSHOOTINGSTAR",
    "CDLSHORTLINE",
    "CDLSPINNINGTOP",
    "CDLSTALLEDPATTERN",
    "CDLSTICKSANDWICH",
    "CDLTAKURI",
    "CDLTASUKIGAP",
    "CDLTHRUSTING",
    "CDLTRISTAR",
    "CDLUNIQUE3RIVER",
    "CDLUPSIDEGAP2CROWS",
    "CDLXSIDEGAP3METHODS",
    "CMO",
    "CORREL",
    "DEMA",
    "DX",
    "EMA",
    "HT_DCPERIOD",
    "HT_DCPHASE",
    "HT_PHASOR",
    "HT_SINE",
    "HT_TRENDLINE",
    "HT_TRENDMODE",
    "KAMA",
    "LINEARREG",
    "LINEARREG_ANGLE",
    "LINEARREG_INTERCEPT",
    "LINEARREG_SLOPE",
    "MA",
    "MACD",
    "MACDEXT",
    "MACDFIX",
    "MAMA",
    "MAX",
    "MAXINDEX",
    "MEDPRICE",
    "MFI",
    "MIDPOINT",
    "MIDPRICE",
    "MIN",
    "MININDEX",
    "MINMAX",
    "MINMAXINDEX",
    "MINUS_DI",
    "MINUS_DM",
    "MOM",
    "NATR",
    "OBV",
    "PLUS_DI",
    "PLUS_DM",
    "PPO",
    "ROC",
    "ROCP",
    "ROCR",
    "ROCR100",
    "RSI",
    "SAR",
    "SAREXT",
    "SMA",
    "STDDEV",
    "STOCH",
    "STOCHF",
    "STOCHRSI",
    "SUM",
    "T3",
    "TEMA",
    "TRANGE",
    "TRIMA",
    "TRIX",
    "TSF",
    "TYPPRICE",
    "ULTOSC",
    "VAR",
    "WCLPRICE",
    "WILLR",
    "WMA",
}


def _slug_to_id(slug: str) -> str:
    return slug.upper()


def _exclude_slug(slug: str) -> bool:
    upper = _slug_to_id(slug)
    if upper in TALIB_UPPER:
        return True
    if slug.startswith("cdl_"):
        return True
    return False


def main() -> None:
    import pandas as pd
    import pandas_ta_classic as ta  # noqa: F401

    frame = pd.DataFrame(
        {
            "open": [1.0, 2.0, 3.0, 4.0, 5.0] * 30,
            "high": [2.0, 3.0, 4.0, 5.0, 6.0] * 30,
            "low": [0.5, 1.5, 2.5, 3.5, 4.5] * 30,
            "close": [1.5, 2.5, 3.5, 4.5, 5.5] * 30,
            "volume": [100.0] * 150,
        }
    )
    slugs = sorted(frame.ta.indicators(as_list=True))
    ids = sorted({_slug_to_id(s) for s in slugs if not _exclude_slug(s)})

    OUT_PY.parent.mkdir(parents=True, exist_ok=True)
    OUT_PY.write_text(
        '"""Auto-generated pandas-ta-classic IDs — run scripts/gen-pandas-ta-catalog.py."""\n\n'
        f"PANDAS_TA_FUNCTION_NAMES: tuple[str, ...] = {tuple(ids)!r}\n",
        encoding="utf-8",
    )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"source": "pandas-ta-classic", "count": len(ids), "ids": ids}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(ids)} pandas-ta-classic IDs to {OUT_PY.name}")


if __name__ == "__main__":
    main()
