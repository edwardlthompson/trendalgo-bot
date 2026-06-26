from trendalgo.risk.config import RiskLimits
from trendalgo.risk.protections import build_protections, merge_risk_into_config, validate_pre_live


def test_build_protections() -> None:
    prot = build_protections(RiskLimits())
    assert any(p["method"] == "MaxDrawdown" for p in prot)


def test_validate_pre_live_blocks_without_approval() -> None:
    errs = validate_pre_live({"dry_run": False}, go_live_approved=False)
    assert any("go-live" in e for e in errs)


def test_merge_risk_dry_run() -> None:
    cfg = merge_risk_into_config(
        {"dry_run": True, "stake_amount": 200}, RiskLimits(max_stake_usd=100)
    )
    assert cfg["stake_amount"] == 100
    assert "protections" in cfg
