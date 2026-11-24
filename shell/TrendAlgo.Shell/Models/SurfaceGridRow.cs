namespace TrendAlgo.Shell.Models;

public sealed class SurfaceGridRow
{
    public string Col1 { get; init; } = "";
    public string Col2 { get; init; } = "";
    public string Col3 { get; init; } = "";
    public string Col4 { get; init; } = "";
    public string Col5 { get; init; } = "";
    public string? HeatHex { get; set; }
    public string Role { get; init; } = ""; // "", "oracle", "bh"

    // Extra fields for Results popup column filters (mirrors backtest_row_filter).
    public string Indicator { get; init; } = "";
    public string Timeframe { get; init; } = "";
    public string ParamsText { get; init; } = "";
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
}
