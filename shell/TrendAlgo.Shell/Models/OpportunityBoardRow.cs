using Avalonia.Media.Imaging;

namespace TrendAlgo.Shell.Models;

/// <summary>LTS desk row — column set mirrors SCANNER_LTS_HEADERS.</summary>
public sealed class OpportunityBoardRow
{
    public bool Watch { get; init; }
    public string WatchGlyph => Watch ? "★" : "☆";
    public string WatchColorHex => Watch ? "#F59E0B" : "#6B7280";
    public string Logo { get; init; } = "·";
    public Bitmap? LogoImage { get; init; }
    public bool HasLogoImage => LogoImage is not null;
    public string Name { get; init; } = "";
    public string Pair { get; init; } = "";
    public double Gain7d { get; init; }
    public string Spark7d { get; init; } = "—";
    public IReadOnlyList<double> SparkCloses7d { get; init; } = Array.Empty<double>();
    public double Gain30d { get; init; }
    public string Spark30d { get; init; } = "—";
    public IReadOnlyList<double> SparkCloses30d { get; init; } = Array.Empty<double>();
    public bool Spark7Up => SparkCloses7d.Count >= 2
        ? SparkCloses7d[^1] >= SparkCloses7d[0]
        : Gain7d >= 0;
    public bool Spark30Up => SparkCloses30d.Count >= 2
        ? SparkCloses30d[^1] >= SparkCloses30d[0]
        : Gain30d >= 0;
    public double BestBtPct { get; init; }
    public double? BotVsBhPct { get; init; }
    public string Health { get; init; } = "";
    public double? HealthScore { get; init; }
    public double? ChartDist7dPct { get; init; }
    public double? ChartDist30dPct { get; init; }
    public double? VolumeAccelPct { get; init; }
    public double Hv7d { get; init; }
    public double MaxDd { get; init; }
    public double VolDelta { get; init; }
    public string Exchange { get; init; } = "";
    public string VolumeUnit { get; init; } = "";
    public double Volume24h { get; init; }
    public string Events { get; init; } = "";
    public string Backtest { get; init; } = "—";
    public bool HasBacktestResults => Backtest == "Results";
    public string BotBestLabel { get; init; } = "";
    public double Gain { get; init; }
    public double VolumeScore { get; init; }
    public string OhlcvSource { get; init; } = "";
    public string Regime { get; init; } = "";
    public double Score { get; init; }
    public double Price { get; init; }
    public string Heat { get; init; } = "";
    public string PayloadJson { get; init; } = "{}";

    public string? HeatGain7d { get; set; }
    public string? HeatGain30d { get; set; }
    public string? HeatBestBt { get; set; }
    public string? HeatBotVsBh { get; set; }
    public string? HeatHealth { get; set; }
    public string? HeatHv7d { get; set; }
    public string? HeatMaxDd { get; set; }
    public string? HeatVolDelta { get; set; }
    public string? HeatVolume24h { get; set; }

    public string Gain7dText => Gain7d.ToString("0.##");
    public string Gain30dText => Gain30d.ToString("0.##");
    public string BestBtText => BestBtPct.ToString("0.##");
    public string BestTaText
    {
        get
        {
            var raw = BotBestLabel.Trim();
            if (raw.Length == 0)
                return "—";
            // Legacy "INDICATOR 3h" → "3h INDICATOR"; already "3h INDICATOR" stays.
            var parts = raw.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length >= 2 && LooksLikeTimeframe(parts[^1]) && !LooksLikeTimeframe(parts[0]))
                return $"{parts[^1]} {string.Join(' ', parts[..^1])}";
            return raw;
        }
    }

    private static bool LooksLikeTimeframe(string token)
    {
        if (token.Length < 2)
            return false;
        var unit = token[^1];
        if (unit is not ('m' or 'h' or 'd' or 'w'))
            return false;
        return int.TryParse(token.AsSpan(0, token.Length - 1), out _);
    }
    public string BotVsBhText => BotVsBhPct?.ToString("0.##") ?? "—";
    public string Hv7dText => Hv7d.ToString("0.##");
    public string MaxDdText => MaxDd.ToString("0.##");
    public string VolDeltaText =>
        VolumeAccelPct is null
            ? "—"
            : VolumeAccelPct.Value.ToString("+0.0;-0.0;0.0", System.Globalization.CultureInfo.InvariantCulture) + "%";
    public string Volume24hText =>
        TrendAlgo.Shell.Services.MoneyFormat.Volume(Volume24h, VolumeUnit, Exchange);
    public string ChartDist7dText => ChartDist7dPct is { } d ? $"{d:0.0}%" : "—";
    public string ChartDist30dText => ChartDist30dPct is { } d ? $"{d:0.0}%" : "—";
}
