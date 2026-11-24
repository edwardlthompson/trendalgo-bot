namespace TrendAlgo.Shell.Models;

/// <summary>One All-TA strategy row — columns match BACKTEST_RESULT_HEADERS (minus chart/create widgets).</summary>
public sealed class StrategyResultRow
{
    public string Indicator { get; init; } = "";
    public string Timeframe { get; init; } = "";
    public string Params { get; init; } = "";
    public string NetPctText { get; init; } = "—";
    public string FeesText { get; init; } = "—";
    public string OpenText { get; init; } = "—";
    public string WinsText { get; init; } = "—";
    public string LossesText { get; init; } = "—";
    public string WinPctText { get; init; } = "—";
    public string TslText { get; init; } = "—";
    public string TslHitsText { get; init; } = "—";
    public string TslHitPctText { get; init; } = "—";
    public string StrengthText { get; init; } = "—";
    public string EventsText { get; init; } = "";
    public string Role { get; init; } = ""; // "", "oracle", "bh"
    public bool CanCreateBot =>
        Role is not "oracle" and not "bh"
        && !string.IsNullOrWhiteSpace(Indicator)
        && !Indicator.StartsWith("Oracle", StringComparison.OrdinalIgnoreCase)
        && !Indicator.StartsWith("B&H", StringComparison.Ordinal);

    public double? NetPct { get; init; }
    public double? FeesPaid { get; init; }
    public double? OpenTrades { get; init; }
    public double? Wins { get; init; }
    public double? Losses { get; init; }
    public double? WinPct { get; init; }
    public double? TslPct { get; init; }
    public double? TslHits { get; init; }
    public double? TslHitPct { get; init; }
    public double? Strength { get; init; }
    public string ParamsText { get; init; } = "";

    public string? HeatNet { get; set; }
    public string? HeatFees { get; set; }
    public string? HeatOpen { get; set; }
    public string? HeatWins { get; set; }
    public string? HeatLosses { get; set; }
    public string? HeatWinPct { get; set; }
    public string? HeatTslHits { get; set; }
    public string? HeatTslHitPct { get; set; }
    public string? HeatStrength { get; set; }
}
