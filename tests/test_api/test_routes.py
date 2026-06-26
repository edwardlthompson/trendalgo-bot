import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from trendalgo.api.app import create_app
from trendalgo.api.state import default_state


def client() -> TestClient:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-api-test-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
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
        json={"strategy": "multi-tf-example", "pair": "BTC/USD"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["total_trades"] == 3
    assert body["metrics"]["total_trades"] == 3
    latest = c.get("/api/v1/backtest/latest").json()
    assert latest["result"]["strategy"] == "multi-tf-example"


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
        json={"trades": False, "pnl_swings": True, "fees": True, "scanner": True, "push_enabled": True},
    )
    assert updated.json()["scanner"] is True


def test_portfolio_sync() -> None:
    c = client()
    sync = c.post("/api/v1/portfolio/sync").json()
    assert sync["total_usd"] > 0
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
    added = c.post(
        "/api/v1/bots",
        json={"label": "Grid-2", "strategy_id": "grid-trading", "pair": "ETH/USD"},
    ).json()
    assert len(added["bots"]) >= 2
    bt = c.post(
        "/api/v1/backtest",
        json={"strategy": "smart-dca", "pair": "BTC/USD", "save_to_library": True},
    ).json()
    assert bt.get("library_id")
    lib = c.get("/api/v1/backtest/library").json()
    assert lib["runs"]
    c.post("/api/v1/watchlist", json={"pair": "SOL/USD", "alert_price_pct": 0.05, "alert_pl_usd": 50})
    wl = c.get("/api/v1/watchlist").json()
    assert any(i["pair"] == "SOL/USD" for i in wl["items"])
    hyper = c.post("/api/v1/hyperopt", json={"strategy": "smart-dca", "pair": "BTC/USD"}).json()
    assert hyper["status"] == "queued"
    export = c.get("/api/v1/strategies/smart-dca/export").json()
    assert "smart-dca" in export["json"]


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
    wf = c.post("/api/v1/research/walk-forward", json={"strategy": "multi-tf-example", "pair": "BTC/USD"}).json()
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
        json={"trailing_stop_pct": 0.04, "scale_out_pct": 0.5, "scale_in_enabled": False, "scale_out_enabled": True},
    ).json()
    assert rules["trailing_stop_pct"] == 0.04
    c.post("/api/v1/backtest", json={"strategy": "multi-tf-example", "pair": "BTC/USD", "save_to_library": True})
    lib = c.get("/api/v1/backtest/library").json()
    if lib["runs"]:
        share = c.post(f"/api/v1/backtest/library/{lib['runs'][0]['id']}/share").json()
        shared = c.get(f"/api/v1/backtest/shared/{share['token']}").json()
        assert shared["read_only"]


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
    goals = c.put("/api/v1/portfolio/goals", json={"target_net_worth_usd": 2500, "label": "Target"}).json()
    assert goals["goal"]["target_net_worth_usd"] == 2500
    basket = c.put("/api/v1/portfolio/basket", json={"weights": {"1": 0.7, "2": 0.3}}).json()
    assert basket["weights"]["1"] == 0.7
    share = c.post("/api/v1/portfolio/public-share").json()
    public = c.get(f"/api/v1/public/dashboard/{share['token']}").json()
    assert public["read_only"]
    discord = c.post("/api/v1/notifications/discord/test", json={"message": "hi"}).json()
    assert discord["sent"] is False


def test_sprint10_billing() -> None:
    c = client()
    dash = c.get("/api/v1/billing/dashboard").json()
    assert dash["net_loss_equals_zero_fee"]
    c.post("/api/v1/billing/process-trades").json()
    enrolled = c.post(
        "/api/v1/billing/enroll",
        json={"license_rate_pct": 0.12, "terms_version": "2026-06-draft-1", "accept_terms": True},
    ).json()
    assert enrolled["enrollment"]["enrolled"] == 1
    c.post("/api/v1/billing/process-trades")
    stmt = c.get("/api/v1/billing/statement/2026-06")
    if stmt.status_code == 200:
        assert "signed_hash" in stmt.json()
    settlement = c.get("/api/v1/billing/settlement").json()
    assert settlement["user_initiated_only"]
    assert settlement["auto_withdraw"] is False
    recon = c.get("/api/v1/billing/reconcile").json()
    assert "ok" in recon
    c.post("/api/v1/billing/mark-paid")
    lightning = c.post("/api/v1/billing/lightning-invoice", json={"period": "2026-06", "amount_usd": 10}).json()
    assert lightning["invoice"].startswith("lnbc")


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
