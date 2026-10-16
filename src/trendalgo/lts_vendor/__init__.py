"""Vendored Linear Trend Spotter dashboard artifacts + backtesting library.

File vendor (not a git submodule). See ``vendor_manifest`` and ADR-0013.
"""

from __future__ import annotations

__all__ = ["install_import_shims"]


def install_import_shims() -> None:
    """Register top-level module names expected by vendored LTS backtesting."""
    from trendalgo.lts_vendor.shims import install as _install

    _install()
