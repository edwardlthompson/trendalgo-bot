"""Ollama prompt templates for backtest analysis."""

OLLAMA_BACKTEST_SYSTEM = (
    "You are a quantitative trading assistant. Summarize backtests factually. "
    "Never recommend live trading or position sizes."
)

OLLAMA_BACKTEST_USER = (
    "Backtest JSON:\n{data}\n\n"
    "Return: (1) edge quality (2) risk flags (3) data gaps to investigate."
)
