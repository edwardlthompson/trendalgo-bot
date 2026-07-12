import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state


def client() -> TestClient:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-api-test-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_FEE_SYNC_ON_START"] = "0"
    from trendalgo.exchanges import fees
    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready

    reset_fee_store()
    fees.clear_fee_cache()
    ensure_fee_db_ready(get_fee_store())
    return TestClient(create_app(default_state()))


def test_health() -> None:
    resp = client().get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_pairs() -> None:
    resp = client().get("/api/v1/pairs")
    assert "BTC/USD" in resp.json()["pairs"]


def test_strategies_and_params() -> None:
    c = client()
    listing = c.get("/api/v1/strategies").json()["strategies"]
    assert any(s["id"] == "multi-tf-example" for s in listing)
    params = c.get("/api/v1/strategies/multi-tf-example/params").json()
    assert "rsi_entry" in params["params"]
    updated = c.put(
        "/api/v1/strategies/multi-tf-example/params",
        json={"params": {"rsi_entry": 30}},
    )
    assert updated.json()["params"]["rsi_entry"] == 30


def test_backtest_and_latest() -> None:
    c = client()
    resp = c.post(
        "/api/v1/backtest",
        json={"strategy": "legacy-ui-sample", "pair": "BTC/USD"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["total_trades"] == 3
    assert body["metrics"]["total_trades"] == 3
    latest = c.get("/api/v1/backtest/latest").json()
    assert latest["result"]["strategy"] == "legacy-ui-sample"


def test_dashboard_and_risk_pause() -> None:
    c = client()
    dash = c.get("/api/v1/dashboard").json()
    assert dash["dry_run"] is True
    assert "equity_usd" in dash
    c.post("/api/v1/risk/pause")
    risk = c.get("/api/v1/risk").json()
    assert risk["paused"] is True
    c.post("/api/v1/risk/resume")
    assert c.get("/api/v1/risk").json()["paused"] is False


def test_debug_logs() -> None:
    c = client()
    c.post("/api/v1/risk/pause")
    logs = c.get("/api/v1/debug/logs").json()["logs"]
    assert any("paused" in line for line in logs)


def test_notification_preferences() -> None:
    c = client()
    prefs = c.get("/api/v1/notifications/preferences").json()
    assert prefs["trades"] is True
    updated = c.put(
        "/api/v1/notifications/preferences",
        json={
            "trades": False,
            "pnl_swings": True,
            "fees": True,
            "scanner": True,
            "push_enabled": True,
        },
    )
    assert updated.json()["scanner"] is True


def test_portfolio_sync() -> None:
    c = client()
    sync = c.post("/api/v1/portfolio/sync").json()
    assert sync["exchange_count"] == 9
    assert sync["kraken"]["total_usd"] > 0
    summary = c.get("/api/v1/portfolio/summary").json()
    assert summary["latest"] is not None


def test_portfolio_overview_and_export() -> None:
    c = client()
    c.post("/api/v1/portfolio/sync")
    overview = c.get("/api/v1/portfolio/overview").json()
    assert overview["net_worth_usd"] > 0
    assert overview["holdings"]
    assert "health_score" in overview
    heatmap = c.get("/api/v1/portfolio/heatmap").json()
    assert "rows" in heatmap
    inbox = c.get("/api/v1/notifications/inbox").json()
    assert "items" in inbox
    export = c.get("/api/v1/portfolio/export")
    assert "asset" in export.text
    daily = c.post("/api/v1/portfolio/daily-notification").json()
    assert "sent" in daily


def test_sprint6_bots_library_watchlist() -> None:
    c = client()
    bots = c.get("/api/v1/bots").json()
    assert bots["bots"]
    limits = c.get("/api/v1/bots/limits").json()
    assert limits["max_bots_total"] == 500
    assert limits["bot_count"] == len(bots["bots"])
    assert limits["enabled_count"] == sum(1 for b in bots["bots"] if b["enabled"])
    assert limits["ohlcv_cache"]["bot_scoped"] is True
    assert limits["ta_cache"]["shared_fingerprint"] is True
    ta_stats = c.get("/api/v1/bots/ta-cache/stats").json()
    assert "hits_exact" in ta_stats
    assert "max_entries" in ta_stats
    cache = c.get("/api/v1/bots/ohlcv/cache").json()
    assert cache["bot_scoped"] is True
    warmup = c.post("/api/v1/bots/ohlcv/warmup").json()
    assert warmup["status"] in {"running", "complete"}
    added = c.post(
        "/api/v1/bots",
        json={"label": "Grid-2", "strategy_id": "grid-trading", "pair": "ETH/USD"},
    ).json()
    assert len(added["bots"]) >= 2
    bt = c.post(
        "/api/v1/backtest",
        json={"strategy": "smart-dca", "pair": "BTC/USD"},
    ).json()
    assert bt.get("result") is not None
    c.post(
        "/api/v1/watchlist", json={"pair": "SOL/USD", "alert_price_pct": 0.05, "alert_pl_usd": 50}
    )
    wl = c.get("/api/v1/watchlist").json()
    assert any(i["pair"] == "SOL/USD" for i in wl["items"])
    hyper = c.post("/api/v1/hyperopt", json={"strategy": "smart-dca", "pair": "BTC/USD"}).json()
    assert hyper["status"] == "queued"
    export = c.get("/api/v1/strategies/smart-dca/export").json()
    assert "smart-dca" in export["json"]


def test_ta_cache_stats_and_config_invalidation() -> None:
    from trendalgo.ta.cache import reset_all_ta_caches

    reset_all_ta_caches()
    c = client()
    bots = c.get("/api/v1/bots").json()["bots"]
    bot_id = bots[0]["id"]
    before = c.get("/api/v1/bots/ta-cache/stats").json()
    detail = c.get(f"/api/v1/bots/{bot_id}").json()
    assert "ta_cache_meta" in detail
    after_detail = c.get("/api/v1/bots/ta-cache/stats").json()
    assert after_detail["misses_full"] >= before["misses_full"]
    bot = detail["bot"]
    c.put(
        f"/api/v1/bots/{bot_id}",
        json={
            "label": bot["label"],
            "strategy_id": "MACD",
            "pair": bot["pair"],
            "equity_usd": bot["equity_usd"],
            "timeframe": bot["timeframe"],
            "exchange": bot.get("exchange", "kraken"),
            "ta_params": {},
        },
    )
    stats = c.get("/api/v1/bots/ta-cache/stats").json()
    assert stats["invalidations_config"] >= 1


def test_bot_detail_trades_zero_skips_ta_cache_meta() -> None:
    from trendalgo.ta.cache import reset_all_ta_caches

    reset_all_ta_caches()
    c = client()
    bots = c.get("/api/v1/bots").json()["bots"]
    bot_id = bots[0]["id"]
    before = c.get("/api/v1/bots/ta-cache/stats").json()
    detail = c.get(f"/api/v1/bots/{bot_id}?trades=0").json()
    after = c.get("/api/v1/bots/ta-cache/stats").json()
    assert detail["simulated_trades"] == []
    assert "ta_cache_meta" not in detail
    assert after["misses_full"] == before["misses_full"]


def test_tradingview_webhook_rejects_unsigned() -> None:
    c = client()
    resp = c.post("/api/v1/webhooks/tradingview", content=b"{}")
    assert resp.json()["accepted"] is False


def test_scanner_run_and_settings() -> None:
    c = client()
    settings = c.get("/api/v1/scanner/settings").json()
    assert settings["interval_minutes"] == 60
    updated = c.put(
        "/api/v1/scanner/settings",
        json={
            "interval_minutes": 30,
            "min_volume_usd": 100000,
            "min_gain_pct": 0.02,
            "min_uniformity": 0.55,
            "universe_filter": "kraken-spot",
            "trendspotter_boost": True,
        },
    )
    assert updated.json()["interval_minutes"] == 30
    run = c.post("/api/v1/scanner/run").json()
    assert run["opportunities"]
    snap = c.get("/api/v1/scanner/snapshot").json()
    assert snap["scan_id"] > 0
    c.post("/api/v1/scanner/watchlist", json={"pair": "ETH/USD"})
    pins = c.get("/api/v1/scanner/watchlist").json()["pairs"]
    assert "ETH/USD" in pins
    bot_pairs = c.get("/api/v1/scanner/pairs-for-bot").json()["pairs"]
    assert bot_pairs


def test_sprint7_research_export() -> None:
    c = client()
    wf = c.post(
        "/api/v1/research/walk-forward", json={"strategy": "multi-tf-example", "pair": "BTC/USD"}
    ).json()
    assert wf["status"] == "complete"
    assert wf.get("engine") == "native"
    mc = c.post("/api/v1/research/monte-carlo").json()
    assert "p50" in mc
    hub = c.get("/api/v1/export/hub").json()
    assert hub["exports"]
    tax = c.get("/api/v1/export/tax")
    assert "pair" in tax.text
    corr = c.get("/api/v1/research/correlation").json()
    assert corr["suggestions"]
    rules = c.put(
        "/api/v1/strategies/exit-rules",
        json={
            "trailing_stop_pct": 0.04,
            "scale_out_pct": 0.5,
            "scale_in_enabled": False,
            "scale_out_enabled": True,
        },
    ).json()
    assert rules["trailing_stop_pct"] == 0.04
    c.post(
        "/api/v1/backtest",
        json={"strategy": "multi-tf-example", "pair": "BTC/USD"},
    )


def test_sprint8_portfolio_advanced() -> None:
    c = client()
    sync = c.post("/api/v1/portfolio/sync-all").json()
    assert sync["kraken"]["mode"] == "dry-run"
    overview = c.get("/api/v1/portfolio/overview").json()
    assert overview.get("exchange_count", 0) >= 2
    c.put("/api/v1/portfolio/targets", json={"asset": "BTC", "target_pct": 0.5})
    c.put("/api/v1/portfolio/cost-basis/BTC", json={"cost_basis_usd": 400})
    c.put("/api/v1/portfolio/tags/BTC", json={"tag": "L1"})
    rebalance = c.get("/api/v1/portfolio/rebalance").json()
    assert rebalance["manual_only"]
    arb = c.get("/api/v1/portfolio/arbitrage").json()
    assert arb["auto_trade"] is False
    goals = c.put(
        "/api/v1/portfolio/goals", json={"target_net_worth_usd": 2500, "label": "Target"}
    ).json()
    assert goals["goal"]["target_net_worth_usd"] == 2500
    basket = c.put("/api/v1/portfolio/basket", json={"weights": {"1": 0.7, "2": 0.3}}).json()
    assert basket["weights"]["1"] == 0.7
    share = c.post("/api/v1/portfolio/public-share").json()
    public = c.get(f"/api/v1/public/dashboard/{share['token']}").json()
    assert public["read_only"]
    discord = c.post("/api/v1/notifications/discord/test", json={"message": "hi"}).json()
    assert discord["sent"] is False


def test_sprint10_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_BTC_USD_RATE", "100000")
    c = client()
    dash = c.get("/api/v1/billing/dashboard").json()
    assert dash["net_loss_equals_zero_fee"]
    assert dash["payment_auto_verify"] is True
    assert "billing_eligibility" in dash
    c.post("/api/v1/billing/process-trades").json()
    enrolled = c.post(
        "/api/v1/billing/enroll",
        json={"license_rate_pct": 0.12, "terms_version": "2026-06-draft-1", "accept_terms": True},
    ).json()
    assert enrolled["enrollment"]["enrolled"] == 1
    from pathlib import Path

    from trendalgo.billing.store import BillingStore

    data_dir = Path(os.environ["TRENDALGO_DATA_DIR"])
    store = BillingStore(data_dir / "billing.db")
    store.set_billing_eligibility("2025-01-01T00:00:00+00:00", "2025-01-01T00:00:00+00:00")
    c.post("/api/v1/billing/process-trades")
    stmt = c.get("/api/v1/billing/statement/2026-06")
    if stmt.status_code == 200:
        assert "signed_hash" in stmt.json()
    settlement = c.get("/api/v1/billing/settlement").json()
    assert settlement["user_initiated_only"]
    assert settlement["auto_withdraw"] is False
    assert settlement["auto_verify"] is True
    assert settlement.get("payment_id") or settlement.get("id")
    payment_id = settlement.get("payment_id") or settlement.get("id")
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    confirmed = c.get(f"/api/v1/billing/payment/status/{payment_id}").json()
    assert confirmed["verified"] is True
    recon = c.get("/api/v1/billing/reconcile").json()
    assert "ok" in recon
    lightning = c.post(
        "/api/v1/billing/lightning-invoice", json={"period": "2026-06", "amount_usd": 10}
    )
    assert lightning.status_code == 501
    assert "not available" in lightning.json()["detail"].lower()


def test_sprint11_ai_growth() -> None:
    c = client()
    recs = c.get("/api/v1/ai/recommendations").json()
    assert recs["recommendations"] and recs["disclaimer"]
    curated = c.get("/api/v1/ai/curated-library").json()
    assert curated["presets"] and not curated["user_uploads"]
    draft = c.post("/api/v1/ai/nl-draft", json={"text": "grid trading rsi 30"}).json()
    assert draft["requires_user_confirmation"]
    ref = c.get("/api/v1/growth/referral").json()
    assert ref["code"] and ref["pseudonymous_only"]
    c.post("/api/v1/growth/leaderboard/opt-in", json={"score_usd": 1000})
    lb = c.get("/api/v1/growth/leaderboard").json()
    assert lb["no_pii"] and lb["rows"]
    boost = c.post("/api/v1/billing/boost-mode").json()
    assert boost["boost_mode"] and boost["license_rate_pct"] == 0.15


def test_fleet_exchange_fees() -> None:
    c = client()
    resp = c.get("/api/v1/backtest/exchange-fees")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "retail_default"
    assert any(row["exchange_id"] == "kraken" for row in body["exchanges"])

    catalog = c.get("/api/v1/exchanges/fees")
    assert catalog.status_code == 200
    assert catalog.json()["venue_count"] >= 5

    checks = c.get("/api/v1/exchanges/fees/checks")
    assert checks.status_code == 200
    assert "checks" in checks.json()


def test_fleet_preflight_bad_pair() -> None:
    c = client()
    resp = c.post(
        "/api/v1/backtest/fleet",
        json={"exchange_id": "kraken", "pair": "NOTREAL/USD"},
    )
    assert resp.status_code == 400


def test_fleet_start_and_complete(monkeypatch) -> None:
    import time

    import trendalgo.backtest.fleet_runner as fleet_runner_mod

    os.environ["TRENDALGO_MARKET_SOURCE"] = "synthetic"
    monkeypatch.setattr(fleet_runner_mod, "TRADINGVIEW_INTERVALS", ("60",))
    monkeypatch.setattr(fleet_runner_mod, "all_strategies", lambda: ("RSI", "MACD", "ROC"))

    c = client()
    resp = c.post(
        "/api/v1/backtest/fleet",
        json={"exchange_id": "kraken", "pair": "BTC/USD", "stake_usd": 1000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["total_combinations"] == 3

    active = body
    for _ in range(120):
        if active.get("status") in ("complete", "error"):
            break
        time.sleep(0.25)
        active = c.get("/api/v1/backtest/fleet/active").json()

    assert active["status"] == "complete"
    assert active.get("elapsed_seconds", 0) >= 0
    latest = c.get("/api/v1/backtest/fleet/latest").json()
    assert "rankings" in latest
    summary = latest.get("summary") or {}
    assert summary.get("buy_and_hold") is not None
    assert summary.get("lookback_days") == 30
    assert "optimized_top10" in summary
    assert isinstance(summary.get("optimized_top10"), list)
    assert "final_top10" in summary
    assert isinstance(summary.get("final_top10"), list)
    assert len(summary.get("final_top10") or []) <= 10

    history = c.get("/api/v1/backtest/fleet/history").json()
    assert "runs" in history
    assert history.get("total", 0) >= 1
    job_id = history["runs"][0]["job_id"]
    saved = c.get(f"/api/v1/backtest/fleet/history/{job_id}").json()
    assert saved["job_id"] == job_id
    assert saved.get("final_top10") is not None or saved.get("summary", {}).get("final_top10")
