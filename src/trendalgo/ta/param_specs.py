"""Default parameter specs for TA-Lib indicators used as bot strategies."""

from __future__ import annotations

from trendalgo.templates.schema import TemplateParamSpec

_DEFAULT_PERIOD = TemplateParamSpec(key="timeperiod", label="Period", default=14, min=2, max=200)

_TA_PARAM_SPECS: dict[str, list[TemplateParamSpec]] = {
    "RSI": [_DEFAULT_PERIOD],
    "MACD": [
        TemplateParamSpec(key="fastperiod", label="Fast period", default=12, min=2, max=100),
        TemplateParamSpec(key="slowperiod", label="Slow period", default=26, min=2, max=200),
        TemplateParamSpec(key="signalperiod", label="Signal period", default=9, min=2, max=50),
    ],
    "SMA": [_DEFAULT_PERIOD],
    "EMA": [_DEFAULT_PERIOD],
    "BBANDS": [
        _DEFAULT_PERIOD,
        TemplateParamSpec(key="nbdevup", label="Upper deviation", default=2.0, min=0.5, max=5),
        TemplateParamSpec(key="nbdevdn", label="Lower deviation", default=2.0, min=0.5, max=5),
    ],
    "ATR": [_DEFAULT_PERIOD],
    "STOCH": [
        TemplateParamSpec(key="fastk_period", label="Fast K", default=5, min=2, max=50),
        TemplateParamSpec(key="slowk_period", label="Slow K", default=3, min=1, max=20),
        TemplateParamSpec(key="slowd_period", label="Slow D", default=3, min=1, max=20),
    ],
}


def ta_param_specs(ta_id: str) -> list[TemplateParamSpec]:
    if ta_id in _TA_PARAM_SPECS:
        return _TA_PARAM_SPECS[ta_id]
    if ta_id.startswith("CDL"):
        return []
    return [_DEFAULT_PERIOD]
