"""User-facing OHLCVT mix / status strings."""

from __future__ import annotations

from datetime import date

from trendalgo.market.kraken_ohlcvt_meta import (
    ArchiveCoverage,
    bands_can_mix,
    mix_allowed,
    rolling_bands_ready,
    rolling_ready_date,
    today_utc,
)


def format_subhour_mix_note(
    coverage: ArchiveCoverage | None,
    *,
    journal_started: date | None = None,
    today: date | None = None,
) -> str:
    day = today_utc(today=today)
    started = journal_started or day
    ready_s = rolling_ready_date(started).isoformat()
    started_s = started.isoformat()
    if mix_allowed(coverage, journal_started=journal_started, today=day):
        if bands_can_mix(coverage, today=day) and coverage is not None and coverage.end:
            return (
                f"1m history covers through {coverage.end.isoformat()}. "
                f"Sub-hour and 1h–24h may activate together."
            )
        return (
            f"Rolling tip journal (started {started_s}) reached 30d on {ready_s}. "
            f"Sub-hour and 1h–24h may activate together."
        )
    if coverage is None or coverage.end is None:
        return (
            f"Cannot mix with 1h–24h yet. Rolling tip journal starts {started_s} — "
            f"30d backtest depth ready on {ready_s}. Or apply Kraken’s next quarterly "
            f"OHLCVT to cover through today and unlock sooner."
        )
    end_s = coverage.end.isoformat()
    return (
        f"Cannot mix with 1h–24h yet. Archive 1m ends {end_s}. "
        f"Rolling tip journal started {started_s} — 30d backtest depth ready on {ready_s}. "
        f"Or apply Kraken’s next quarterly OHLCVT to backfill {end_s} → today and unlock sooner."
    )


def format_ohlcvt_status(
    coverage: ArchiveCoverage | None,
    *,
    journal_started: date | None = None,
    today: date | None = None,
) -> str:
    day = today_utc(today=today)
    started = journal_started or day
    ready_s = rolling_ready_date(started).isoformat()
    started_s = started.isoformat()
    if coverage is None or coverage.end is None:
        return (
            f"OHLCVT ready for sub-hour depth. 30d rolling tip ready on {ready_s} "
            f"(journal from {started_s}), or when quarterly coverage reaches today."
        )
    end_s = coverage.end.isoformat()
    if bands_can_mix(coverage, today=day):
        return (
            f"OHLCVT ready (through {end_s}). Gap filled — "
            f"sub-hour and 1h–24h may activate together."
        )
    if rolling_bands_ready(journal_started, today=day):
        return (
            f"OHLCVT ready (through {end_s}). Rolling 30d tip journal ready — "
            f"sub-hour and 1h–24h may activate together."
        )
    return (
        f"OHLCVT ready for sub-hour (through {end_s}). "
        f"Rolling tip journal from {started_s} — 30d depth ready on {ready_s}. "
        f"Quarterly OHLCVT can backfill {end_s} → today and unlock sooner."
    )
