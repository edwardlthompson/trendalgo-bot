using System.Globalization;
using System.Text.Json;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

/// <summary>Relative green→yellow→red rank fills (PySide scanner_heat parity).</summary>
public static class BoardHeatRanker
{
    private static readonly (int R, int G, int B) Red = (220, 38, 38);
    private static readonly (int R, int G, int B) Yellow = (234, 179, 8);
    private static readonly (int R, int G, int B) Green = (22, 163, 74);

    public static bool HeatmapEnabled()
    {
        return FlagTrue("scanner_filters.json", "heatmap_enabled")
            || FlagTrue("results_view_prefs.json", "heatmap_enabled");
    }

    private static bool FlagTrue(string fileName, string key)
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, fileName);
        if (!File.Exists(path))
            return false;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            return doc.RootElement.TryGetProperty(key, out var p)
                && p.ValueKind == JsonValueKind.True;
        }
        catch
        {
            return false;
        }
    }

    public static void Apply(IList<OpportunityBoardRow> rows)
    {
        if (rows.Count == 0 || !HeatmapEnabled())
            return;

        Assign(rows, Rank(rows.Select(r => (double?)r.Gain7d).ToList()), (r, c) => r.HeatGain7d = c);
        Assign(rows, Rank(rows.Select(r => (double?)r.Gain30d).ToList()), (r, c) => r.HeatGain30d = c);
        Assign(rows, Rank(rows.Select(r => (double?)r.BestBtPct).ToList()), (r, c) => r.HeatBestBt = c);
        Assign(
            rows,
            Rank(rows.Select(r => r.BotVsBhPct).ToList()),
            (r, c) => r.HeatBotVsBh = c);
        Assign(
            rows,
            Rank(rows.Select(r => r.HealthScore).ToList()),
            (r, c) => r.HeatHealth = c);
        Assign(
            rows,
            Rank(rows.Select(r => (double?)r.Hv7d).ToList(), invert: true),
            (r, c) => r.HeatHv7d = c);
        Assign(
            rows,
            Rank(rows.Select(r => (double?)r.MaxDd).ToList(), invert: true),
            (r, c) => r.HeatMaxDd = c);
        Assign(rows, Rank(rows.Select(r => (double?)r.VolDelta).ToList()), (r, c) => r.HeatVolDelta = c);
        Assign(rows, Rank(rows.Select(r => (double?)r.Volume24h).ToList()), (r, c) => r.HeatVolume24h = c);
    }

    private static void Assign(
        IList<OpportunityBoardRow> rows,
        IReadOnlyList<string?> colors,
        Action<OpportunityBoardRow, string?> set)
    {
        for (var i = 0; i < rows.Count; i++)
            set(rows[i], colors[i]);
    }

    public static IReadOnlyList<string?> Rank(IReadOnlyList<double?> values, bool invert = false)
    {
        var outColors = new string?[values.Count];
        var ranked = new List<(int Index, double Value)>();
        for (var i = 0; i < values.Count; i++)
        {
            var v = values[i];
            if (v is double d && !double.IsNaN(d))
                ranked.Add((i, d));
        }
        if (ranked.Count == 0)
            return outColors;

        var buckets = new SortedDictionary<double, List<int>>();
        foreach (var (index, value) in ranked)
        {
            var key = Math.Round(value, 8);
            if (!buckets.TryGetValue(key, out var list))
            {
                list = new List<int>();
                buckets[key] = list;
            }
            list.Add(index);
        }

        var unique = invert
            ? buckets.Keys.ToList()
            : buckets.Keys.Reverse().ToList();
        if (unique.Count == 1)
        {
            var color = LerpRyg(1.0);
            foreach (var index in buckets[unique[0]])
                outColors[index] = color;
            return outColors;
        }

        var last = unique.Count - 1;
        for (var place = 0; place < unique.Count; place++)
        {
            var t = 1.0 - (place / (double)last);
            var color = LerpRyg(t);
            foreach (var index in buckets[unique[place]])
                outColors[index] = color;
        }
        return outColors;
    }

    private static string LerpRyg(double t)
    {
        t = Math.Clamp(t, 0, 1);
        return t <= 0.5 ? Mix(Red, Yellow, t * 2) : Mix(Yellow, Green, (t - 0.5) * 2);
    }

    private static string Mix((int R, int G, int B) a, (int R, int G, int B) b, double u)
    {
        int Ch(int x, int y) => (int)(x + (y - x) * u);
        return string.Format(
            CultureInfo.InvariantCulture,
            "#{0:X2}{1:X2}{2:X2}",
            Ch(a.R, b.R),
            Ch(a.G, b.G),
            Ch(a.B, b.B));
    }
}
