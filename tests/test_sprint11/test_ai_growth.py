"""Sprint 11 AI & growth tests."""

from trendalgo.ai.curated_library import list_curated
from trendalgo.ai.nl_draft import rule_based_draft
from trendalgo.ai.recommender import recommend_strategies
from trendalgo.ai.scanner_pipeline import pipeline_suggestions
from trendalgo.billing.boost import enable_boost_mode
from trendalgo.billing.store import BillingStore
from trendalgo.growth.store import GrowthStore, pseudonymous_code


def test_recommender_and_pipeline() -> None:
    opps = [{"pair": "ETH/USD", "uniformity": 0.7, "gain_pct": 0.05}]
    recs = recommend_strategies(opps, {"drawdown_pct": 0.02, "equity_usd": 1000})
    assert recs and recs[0]["requires_backtest"]
    pipe = pipeline_suggestions(opps)
    assert pipe[0]["template_id"] == "strong-uptrend-scanner"


def test_nl_draft_and_curated() -> None:
    draft = rule_based_draft("DCA accumulate with rsi entry 28")
    assert draft["strategy_id"] == "smart-dca"
    assert draft["requires_user_confirmation"]
    lib = list_curated()
    assert not lib["user_uploads"] and lib["presets"]


def test_growth_and_boost(tmp_path) -> None:
    store = GrowthStore(tmp_path / "growth.db")
    uuid = "test-uuid-1234"
    ref = store.get_or_create_referral(uuid)
    assert ref["code"] == pseudonymous_code(uuid)
    store.opt_in_leaderboard(uuid, 500.0)
    rows = store.leaderboard_rows()
    assert rows and rows[0]["pseudonym"].startswith("trader-")
    billing = BillingStore(tmp_path / "billing.db")
    boost = enable_boost_mode(billing)
    assert boost["license_rate_pct"] == 0.15
