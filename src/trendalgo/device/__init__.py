"""Local device app (ADR-0016): the PySide6 window for scans, backtests, plans, status, and settings.

Modules outside `views/` and `app.py` import no Qt, so a pool worker can load them without a window (D1).
"""
