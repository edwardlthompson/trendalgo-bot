# Brand voice

Voice for **TrendAlgo Bot**. Keep pitch copy in `product.json` aligned with this file.

## Tone

- **Clear and direct** — say what the app does in one breath (self-hosted trading you run yourself)
- **FOSS-first** — emphasize user control, keys on their VPS, and no default telemetry
- **Confident, not hype** — no “revolutionary” / “ultimate” / “AI-powered alpha” filler
- **Operator-friendly** — dry-run first, explicit go-live, concrete next steps

## Pitch rules

1. Lead with ownership (your VPS, your keys, your data), then the stack (Python + PWA).
2. Keep the elevator pitch to 1–2 sentences.
3. Features are benefits (“dry-run until you approve live”), not internals (“uses FastAPI”).
4. README hero + badges must still read if images fail to load (alt text / headings).

## Do / don’t

| Do | Don’t |
|----|-------|
| Specific verbs: sync, backtest, go live, self-host | Promise guaranteed returns or custodial accounts |
| Link to SECURITY / CONTRIBUTING / go-live gates | Promise proprietary store SDKs or default telemetry |
| Match `product.json` name to PWA `app.title` | Invent a second product name in docs |
