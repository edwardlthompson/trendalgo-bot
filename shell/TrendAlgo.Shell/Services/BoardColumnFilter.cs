using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

/// <summary>Client-side Qualified table filters — mirrors <c>lts_scan_model.filter_coins</c>.</summary>
public static class BoardColumnFilter
{
    public static bool Passes(OpportunityBoardRow row, BoardColumnFilterState f)
    {
        if (!PassMinFloor(row.Gain7d, f.MinGain7d))
            return false;
        if (!PassMinFloor(row.Gain30d, f.MinGain30d))
            return false;
        if (!PassMinFloor(row.BestBtPct, f.MinBestBt))
            return false;
        if (!PassBotVsBh(row.BotVsBhPct, f.BotVsBh))
            return false;
        if (!PassChartDist(row.ChartDist7dPct, f.ChartDistMax7dValue))
            return false;
        if (!PassChartDist(row.ChartDist30dPct, f.ChartDistMax30dValue))
            return false;
        if (f.HealthMin is { } healthFloor)
        {
            if (row.HealthScore is not { } score || score < healthFloor)
                return false;
        }
        if (!PassVolAccel(row.VolumeAccelPct, f.VolAccel))
            return false;
        if (f.Vol24MinValue is { } volFloor)
        {
            if (row.Volume24h < volFloor)
                return false;
        }
        if (!PassExchanges(row.Exchange, f.ViewExchanges))
            return false;
        return true;
    }

    public static IEnumerable<OpportunityBoardRow> Apply(
        IEnumerable<OpportunityBoardRow> rows, BoardColumnFilterState f) =>
        rows.Where(r => Passes(r, f));

    /// <summary>None floor = off; 0 = strictly positive; N&gt;0 = value &gt;= N.</summary>
    public static bool PassMinFloor(double? value, double? floor)
    {
        if (floor is null)
            return true;
        if (value is null)
            return false;
        if (floor == 0)
            return value > 0;
        return value >= floor;
    }

    public static bool PassBotVsBh(double? value, string? filt)
    {
        if (string.IsNullOrWhiteSpace(filt))
            return true;
        if (value is null)
            return false;
        return filt switch
        {
            "pos" => value > 0,
            "neg" => value < 0,
            _ => true,
        };
    }

    public static bool PassChartDist(double? value, double? maxPct)
    {
        if (maxPct is null)
            return true;
        if (value is null)
            return true;
        return value < maxPct;
    }

    public static bool PassVolAccel(double? value, string? filt)
    {
        if (string.IsNullOrWhiteSpace(filt))
            return true;
        if (value is null)
            return false;
        if (filt == "pos")
            return value > 0;
        if (double.TryParse(filt, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out var threshold))
            return value >= threshold;
        return true;
    }

    public static bool PassExchanges(string exchange, IReadOnlyList<string>? allowed)
    {
        if (allowed is null)
            return true;
        var eid = (exchange ?? "").Trim().ToLowerInvariant();
        if (allowed.Count == 0)
            return false;
        return allowed.Any(a => string.Equals(a, eid, StringComparison.OrdinalIgnoreCase)
            || eid.Contains(a, StringComparison.OrdinalIgnoreCase));
    }
}
