import hashlib
import hmac
import json
from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.signals.tradingview import TradingViewWebhook


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_accepts_valid_hmac(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    secret = "test-secret"
    handler = TradingViewWebhook(store, secret=secret, allowlist=frozenset({"127.0.0.1"}))
    payload = json.dumps({"pair": "BTC/USD", "action": "buy"}).encode()
    result = handler.handle(payload, client_ip="127.0.0.1", signature=_sign(secret, payload))
    assert result.accepted is True
    assert result.signal is not None


def test_webhook_rejects_bad_ip(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    handler = TradingViewWebhook(store, secret="s", allowlist=frozenset({"10.0.0.1"}))
    payload = b"{}"
    result = handler.handle(payload, client_ip="127.0.0.1", signature="bad")
    assert result.accepted is False
