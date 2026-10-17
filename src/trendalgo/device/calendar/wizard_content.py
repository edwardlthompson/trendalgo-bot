"""Calendar API wizard copy with cited official sources."""

from __future__ import annotations

from datetime import date

from trendalgo.device.wizard.model import Source, Step

CHECKED = date(2026, 10, 16)

CMC_DOCS = Source(
    "CoinMarketCal API Docs",
    "https://coinmarketcal.com/developer/docs",
    CHECKED,
)
CMC_KEYS = Source(
    "CoinMarketCal API Authentication",
    "https://coinmarketcal.com/developer/docs/authentication",
    CHECKED,
)
COINDAR_API = Source(
    "Coindar API 2.0",
    "https://coindar.org/en/api",
    CHECKED,
)
COINDAR_TOKENS = Source(
    "Coindar access tokens",
    "https://coindar.org/en/api/tokens",
    CHECKED,
)

STEPS: tuple[Step, ...] = (
    Step(
        "W-CAL-0",
        "Why calendar APIs",
        (
            "The Events Calendar shows upcoming crypto listings, conferences, and other dated "
            "news for coins you hold. Providers are optional.",
            "API keys stay on this PC in Windows Credential Manager. TrendAlgo never scrapes "
            "calendar websites and never commits your keys to a file.",
            "You can skip a provider and enable it later from Settings or the calendar module.",
        ),
    ),
    Step(
        "W-CAL-1",
        "CoinMarketCal (recommended)",
        (
            "Open the CoinMarketCal developer site, create an account, and mint an API key.",
            "Paste the key below, click Test, then Save. Free tiers limit how far ahead events "
            "appear; paid tiers unlock impact scores used for High/Medium filters.",
        ),
        (CMC_DOCS, CMC_KEYS),
    ),
    Step(
        "W-CAL-2",
        "Coindar (optional)",
        (
            "Coindar adds popularity ranking (views) and tag filters. Register, open the tokens "
            "page, and create an access token.",
            "Paste the token, Test, then Save. You can skip this step if CoinMarketCal alone is enough.",
        ),
        (COINDAR_API, COINDAR_TOKENS),
    ),
    Step(
        "W-CAL-3",
        "Default filters",
        (
            "Defaults keep noise low: My holdings, next 30 days, and Medium+ impact when scores "
            "are available. Change chips anytime on the Events Calendar module.",
        ),
    ),
    Step(
        "W-CAL-4",
        "Done",
        (
            "TrendAlgo will refresh events into a local cache on this PC. Open the Events "
            "Calendar module on the Dashboard Analytics page to browse upcoming dates.",
        ),
    ),
)
