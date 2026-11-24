"""Exchange API key surface + live read-only verification for Avalonia."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.alpaca_vault import has_alpaca_credentials, resolve_alpaca_credentials
from trendalgo.device.alpaca_verify import verify_alpaca_keys
from trendalgo.device.secrets_vault import VaultEntry, VaultSecretStore
from trendalgo.device.time_display import format_display_time
from trendalgo.exchanges.private_budget import budget_snapshot
from trendalgo.exchanges.private_client import ccxt_client, set_secret_store
from trendalgo.exchanges.registry import get_entry, load_registry
from trendalgo.trading.key_verify import verify_exchange_keys

__all__ = ["load_exchange_keys_surface", "verify_saved_exchange_key"]


def _format_verified(iso_raw: str | None) -> str:
    if not iso_raw:
        return ""
    return format_display_time(iso_raw) or str(iso_raw)


def load_exchange_keys_surface(root: Path) -> dict[str, Any]:
    """Return presence, scope, verification state, and rate budget for all 9 CEXes + Alpaca."""
    del root
    vault = VaultSecretStore()
    vault.bind_registry()
    reg = load_registry()
    rows: list[dict[str, Any]] = []
    configured_count = 0
    for entry in reg.exchanges:
        stored = vault.read_entry(entry.id)
        configured = stored is not None or entry.has_api_keys(vault)
        if configured:
            configured_count += 1
        max_calls = max(1, int(entry.max_private_calls_per_min or 15))
        budget = budget_snapshot(entry.id, max_per_min=max_calls)
        verified_at = stored.verified_at if stored else None
        rows.append(
            {
                "id": entry.id,
                "brand": entry.brand,
                "tier": entry.tier,
                "quote_currency": entry.quote_currency,
                "us_retail": bool(entry.us_retail),
                "us_restricted": bool(entry.us_restricted),
                "needs_passphrase": entry.id == "okx",
                "pem_hint": entry.id == "coinbaseadvanced",
                "configured": configured,
                "scope": stored.scope if stored else "query",
                "verified_at": verified_at or "",
                "verified_local": _format_verified(verified_at),
                "has_passphrase": bool(stored and stored.passphrase),
                "rate_used": int(budget["used"]),
                "rate_max": int(budget["max_calls"]),
            }
        )
    alpaca_creds = resolve_alpaca_credentials()
    alpaca_prefix = ""
    if alpaca_creds is not None:
        kid = alpaca_creds[0]
        alpaca_prefix = f"{kid[:4]}…" if len(kid) >= 4 else "set"
    return {
        "ok": True,
        "exchanges": rows,
        "configured_count": configured_count,
        "alpaca": {
            "configured": has_alpaca_credentials(),
            "key_prefix": alpaca_prefix,
        },
    }


def _human_verify_error(exc: Exception) -> str:
    name = type(exc).__name__
    raw = str(exc).strip()
    lower = raw.lower()
    if "nonce" in lower:
        return (
            "Nonce rejected by exchange — wait 2s and click Verify again (or generate a fresh key)."
        )
    if "passphrase" in lower or "password" in lower:
        return "API Passphrase missing or invalid."
    if "permission" in lower or "scope" in lower:
        return "API key lacks Query/Balance permission."
    if "auth" in name.lower() or "invalid key" in lower or "signature" in lower or "401" in lower:
        return "Authentication failed — check API Key and API Secret (never share or paste spaces)."
    if "pem" in lower or "ec" in lower or "asn1" in lower:
        return "Invalid Coinbase CDP EC private key PEM — paste the full -----BEGIN EC PRIVATE KEY----- block."
    return f"{name}: {raw[:140]}" if raw else name


def verify_saved_exchange_key(root: Path, exchange_id: str) -> dict[str, Any]:
    """Probe the real exchange (read-only fetch_balance) using CredMan/env keys."""
    del root
    eid = str(exchange_id or "").strip().lower()
    if not eid:
        return {"ok": False, "exchange_id": "", "message": "Exchange ID required."}
    if eid == "alpaca":
        creds = resolve_alpaca_credentials()
        if creds is None:
            return {
                "ok": False,
                "exchange_id": "alpaca",
                "message": "Alpaca keys are not configured.",
            }
        ok, msg = verify_alpaca_keys(creds[0], creds[1])
        return {"ok": ok, "exchange_id": "alpaca", "brand": "Alpaca", "message": msg}

    try:
        reg_entry = get_entry(eid)
    except KeyError:
        return {"ok": False, "exchange_id": eid, "message": f"Unknown exchange: {eid}"}

    vault = VaultSecretStore()
    vault.bind_registry()
    stored = vault.read_entry(eid)
    if stored is None and not reg_entry.has_api_keys(vault):
        return {
            "ok": False,
            "exchange_id": eid,
            "brand": reg_entry.brand,
            "message": f"No saved keys found for {reg_entry.brand}. Save keys first.",
        }

    set_secret_store(vault)
    captured_balance: dict[str, Any] = {}
    probe_error: list[str] = []

    def _probe() -> dict[str, Any]:
        client = ccxt_client(reg_entry, store=vault)
        try:
            bal = client.fetch_balance()
        except Exception as exc:
            probe_error.append(_human_verify_error(exc))
            raise
        if isinstance(bal, dict):
            captured_balance.update(bal)
        return bal if isinstance(bal, dict) else {}

    scope = stored.scope if stored is not None else "query"
    result = verify_exchange_keys(exchange_id=eid, scope=scope, fetch_balance=_probe)
    if not result.ok:
        detail = probe_error[0] if probe_error else result.message
        return {
            "ok": False,
            "exchange_id": eid,
            "brand": reg_entry.brand,
            "scope": scope,
            "message": detail,
        }

    if stored is not None:
        vault.write_entry(
            VaultEntry(
                exchange_id=stored.exchange_id,
                api_key=stored.api_key,
                api_secret=stored.api_secret,
                scope=stored.scope,
                verified_at=result.verified_at,
                passphrase=stored.passphrase,
            )
        )

    totals = captured_balance.get("total")
    nonzero = 0
    if isinstance(totals, dict):
        for v in totals.values():
            try:
                if float(v or 0) > 0:
                    nonzero += 1
            except (TypeError, ValueError):
                continue

    return {
        "ok": True,
        "exchange_id": eid,
        "brand": reg_entry.brand,
        "scope": scope,
        "verified_at": result.verified_at or "",
        "verified_local": _format_verified(result.verified_at),
        "nonzero_assets": nonzero,
        "message": f"Connected to {reg_entry.brand} ({scope}) · {nonzero} non-zero asset(s).",
    }
