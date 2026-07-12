"""Lightning invoices — unavailable until a real node is wired."""

from __future__ import annotations

from typing import Any


class LightningUnavailableError(RuntimeError):
    """Raised when Lightning settlement is requested but not implemented."""


def create_lightning_invoice(amount_usd: float, period: str) -> dict[str, Any]:
    """Refuse stub invoices — callers must surface HTTP 501."""
    del amount_usd, period
    raise LightningUnavailableError(
        "Lightning invoicing is not available until a real node is wired."
    )
