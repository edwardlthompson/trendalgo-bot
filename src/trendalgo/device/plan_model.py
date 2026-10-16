"""Plan builder logic: validate bots, check the plan, and build the bundle the host verifies.

The bundle header matches `verify_bundle` in trendalgo.botd.bundle, so a bundle built here is
accepted by a host that uses the same owner id. Catalog indicators may be saved locally;
the host may still refuse non-live strategies on Send.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from trendalgo.botd.bundle import bundle_hash
from trendalgo.device.fields import (
    TIMEFRAMES,
    check_pair,
    check_trailing_stop,
    parse_number,
)
from trendalgo.device.profile import ProfileError

MAX_BOTS = 20
MAX_STAKE_USD = 100_000.0
MAX_NAME_LENGTH = 40
PUBLISHER = "owner"
KEY_ID = "owner-1"
BAD_PLAN = "plan.json has a bot that is not valid. Move the file aside, then build the plan again."


STAKE_FIXED = "fixed_usd"
STAKE_PERCENT = "equity_pct"
STAKE_MODES = (STAKE_FIXED, STAKE_PERCENT)
MAX_EQUITY_PCT = 100.0


@dataclass(frozen=True)
class BotSpec:
    name: str
    pair: str
    timeframe: str
    indicator: str
    stake_usd: float
    trailing_stop_pct: float
    stake_mode: str = STAKE_FIXED
    equity_pct: float = 0.0


def validate_bot(
    *,
    name: str,
    pair: str,
    timeframe: str,
    indicator: str,
    stake: str,
    trailing_stop: str,
    stake_mode: str = STAKE_FIXED,
) -> tuple[BotSpec | None, list[str]]:
    """The spec when every field passes. Otherwise (None, one plain-language message per field)."""
    errors: list[str] = []
    label = name.strip()
    if not 1 <= len(label) <= MAX_NAME_LENGTH:
        errors.append(f"Name: enter 1 to {MAX_NAME_LENGTH} characters.")
    symbol = check_pair(pair)
    if symbol is None:
        errors.append("Pair: use BASE/QUOTE, for example BTC/USD.")
    if timeframe not in TIMEFRAMES:
        errors.append("Timeframe: choose a heartbeat hour from 1h to 24h.")
    if not indicator.strip():
        errors.append("Indicator: enter a strategy or live indicator name.")
    elif len(indicator.strip()) > MAX_NAME_LENGTH:
        errors.append(f"Indicator: keep it under {MAX_NAME_LENGTH} characters.")
    mode = stake_mode.strip() or STAKE_FIXED
    if mode not in STAKE_MODES:
        errors.append("Stake mode: choose fixed USD or percent of equity.")
    amount = parse_number(stake)
    stake_usd = 0.0
    equity_pct = 0.0
    if mode == STAKE_PERCENT:
        if amount is None or not 0 < amount <= MAX_EQUITY_PCT:
            errors.append(f"Stake: enter a percent above 0, up to {MAX_EQUITY_PCT:g}.")
        else:
            equity_pct = amount
    else:
        if amount is None or not 0 < amount <= MAX_STAKE_USD:
            errors.append(f"Stake: enter a USD amount above 0, up to {MAX_STAKE_USD:,.0f}.")
        else:
            stake_usd = amount
    stop = check_trailing_stop(trailing_stop)
    if stop is None:
        errors.append("Trailing stop: enter 0 to turn it off, or a percent from 1 to 20.")
    if errors or symbol is None or amount is None or stop is None:
        return None, errors
    return BotSpec(label, symbol, timeframe, indicator, stake_usd, stop, mode, equity_pct), []


def check_plan(bots: list[BotSpec]) -> list[str]:
    """Plan-level messages: at least one bot, at most MAX_BOTS, and no repeated names."""
    errors: list[str] = []
    if not bots:
        errors.append("Add at least one bot before saving the plan.")
    if len(bots) > MAX_BOTS:
        errors.append(f"A plan holds at most {MAX_BOTS} bots.")
    names = [bot.name.casefold() for bot in bots]
    if len(set(names)) != len(names):
        errors.append("Each bot needs a different name.")
    return errors


def next_plan_version(current: int) -> int:
    """Every save raises the version, because the host refuses a plan that does not increase it."""
    return current + 1


def build_bundle(bots: list[BotSpec], *, owner_id: str, plan_version: int) -> dict[str, Any]:
    payload: dict[str, Any] = {"bots": [asdict(bot) for bot in bots]}
    header: dict[str, Any] = {
        "owner_id": owner_id,
        "publisher": PUBLISHER,
        "kid": KEY_ID,
        "plan_version": plan_version,
        "bundle_hash": bundle_hash(payload),
    }
    return {"header": header, "payload": payload}


def plan_document(plan_version: int, bots: list[BotSpec]) -> dict[str, Any]:
    return {"plan_version": plan_version, "bots": [asdict(bot) for bot in bots]}


def load_plan(document: dict[str, Any] | None) -> tuple[int, list[BotSpec]]:
    """The saved plan as (plan_version, bots). No file gives (0, []). Bad content raises."""
    if document is None:
        return 0, []
    version = document.get("plan_version", 0)
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise ProfileError(BAD_PLAN)
    raw = document.get("bots", [])
    if not isinstance(raw, list):
        raise ProfileError(BAD_PLAN)
    return version, [_spec_from(item) for item in raw]


def _spec_from(item: object) -> BotSpec:
    if not isinstance(item, dict):
        raise ProfileError(BAD_PLAN)
    mode = str(item.get("stake_mode") or STAKE_FIXED)
    stake_value = item.get("equity_pct") if mode == STAKE_PERCENT else item.get("stake_usd")
    spec, errors = validate_bot(
        name=str(item.get("name", "")),
        pair=str(item.get("pair", "")),
        timeframe=str(item.get("timeframe", "")),
        indicator=str(item.get("indicator", "")),
        stake=str(stake_value if stake_value is not None else ""),
        trailing_stop=str(item.get("trailing_stop_pct", "")),
        stake_mode=mode,
    )
    if spec is None or errors:
        raise ProfileError(BAD_PLAN)
    return spec
