using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

/// <summary>Client-side Results popup filters — mirrors <c>backtest_row_filter.row_matches</c>.</summary>
public static class ResultsRowFilter
{
    public static IEnumerable<StrategyResultRow> Apply(
        IEnumerable<StrategyResultRow> rows,
        BacktestFilterState f)
    {
        foreach (var row in rows)
        {
            if (Pass(row, f))
                yield return row;
        }
    }

    public static bool Pass(StrategyResultRow row, BacktestFilterState f)
    {
        if (row.Role is "oracle" or "bh")
            return true;

        var needle = f.IndicatorContains.Trim();
        if (needle.Length > 0
            && row.Indicator.IndexOf(needle, StringComparison.OrdinalIgnoreCase) < 0)
            return false;

        var tf = f.Timeframe.Trim();
        if (tf.Length > 0
            && !string.Equals(row.Timeframe, tf, StringComparison.OrdinalIgnoreCase))
            return false;

        var paramsQ = f.ParamsContains.Trim();
        if (paramsQ.Length > 0
            && row.ParamsText.IndexOf(paramsQ, StringComparison.OrdinalIgnoreCase) < 0)
            return false;

        if (!MinOk(row.NetPct, f.MinNetPct))
            return false;
        if (!MaxOk(row.FeesPaid, f.MaxFees, allowZero: false))
            return false;
        if (!MaxOk(row.OpenTrades, f.MaxOpen, allowZero: true))
            return false;
        if (!MinOk(row.Wins, f.MinWins))
            return false;
        if (!MaxOk(row.Losses, f.MaxLosses, allowZero: true))
            return false;
        if (!MinOk(row.WinPct, f.MinWinPct))
            return false;
        if (!MaxOk(row.TslPct, f.MaxTslPct, allowZero: false))
            return false;
        if (!MaxOk(row.TslHits, f.MaxTslHits, allowZero: true))
            return false;
        if (!MaxOk(row.TslHitPct, f.MaxTslHitPct, allowZero: false))
            return false;
        if (!MinOk(row.Strength, f.MinStrength))
            return false;
        return true;
    }

    private static bool MinOk(double? value, string raw)
    {
        if (!TryBound(raw, out var bound))
            return true;
        return value is { } v && v >= bound;
    }

    private static bool MaxOk(double? value, string raw, bool allowZero)
    {
        if (!TryBound(raw, out var bound))
            return true;
        if (!allowZero && bound <= 0)
            return true;
        return value is { } v && v <= bound;
    }

    private static bool TryBound(string raw, out double bound)
    {
        bound = 0;
        var t = raw.Trim();
        if (t.Length == 0)
            return false;
        return double.TryParse(t, System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture, out bound);
    }
}
