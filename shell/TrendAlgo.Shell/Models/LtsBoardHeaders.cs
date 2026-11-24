namespace TrendAlgo.Shell.Models;

/// <summary>Mirrors <c>SCANNER_LTS_HEADERS</c> / <c>SCANNER_LTS_HEADER_TIPS</c> (+ Best TA board column).</summary>
public static class LtsBoardHeaders
{
    public static readonly string[] Titles =
    [
        "Logo", "Name", "7D %", "7D chart", "30D %", "30D chart",
        "Best BT %", "Best TA", "Bot vs B&H", "Health", "HV 7D", "Max DD",
        "Vol Δ%", "Exchange", "24H Vol", "Events",
    ];

    public static readonly string[] Tips =
    [
        "Coin logo",
        "Asset name (opens listing) with ticker",
        "Seven-day percent gain from snapshot",
        "Seven-day hourly sparkline; % below window high. Orange line is last close.",
        "Thirty-day percent gain from snapshot",
        "Thirty-day hourly sparkline; % below window high. Orange line is last close.",
        "Highest backtest net percent",
        "Winning trailing-stop / TA label for the Best BT % pass",
        "Best BT net % minus All-TA buy-&-hold net % on the same timeframe (not the 30d price-gain column)",
        "Composite health score (gain, volume accel, risk)",
        "Annualized historical volatility from about 7d of hourly closes",
        "Peak-to-trough drawdown over about 30d of hourly closes",
        "Volume acceleration vs baseline window",
        "Listing venue for this row",
        "Approximate 24h USD volume on Kraken spot for this base (all quotes; not CoinMarketCap global)",
        "Open coin event timeline when the local calendar cache has dates in window",
    ];

    public static string Tip(int index) =>
        index >= 0 && index < Tips.Length ? Tips[index] : "";
}
