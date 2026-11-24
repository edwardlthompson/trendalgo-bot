using System.Globalization;
using System.Text.Json;
using Microsoft.Data.Sqlite;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public static class LaneBoardLoader
{
    public static IReadOnlyList<OpportunityBoardRow> Load(string lane, string tab)
    {
        var watchlist = LoadWatchlistSet(lane);
        var fromDb = LoadFromResultsDb(lane, tab, watchlist);
        var rows = fromDb.Count > 0 ? fromDb : LoadFromLtsJson(lane, tab, watchlist);
        if (rows is IList<OpportunityBoardRow> mutable)
            BoardHeatRanker.Apply(mutable);
        else if (rows.Count > 0)
        {
            var copy = rows.ToList();
            BoardHeatRanker.Apply(copy);
            return copy;
        }
        return rows;
    }

    private static HashSet<string> LoadWatchlistSet(string lane)
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var key = (lane ?? "crypto").Trim().ToLowerInvariant();
        var file = key is "" or "crypto"
            ? Path.Combine(ProfilePaths.DeviceRoot, "scanner_watchlist.json")
            : Path.Combine(ProfilePaths.DeviceRoot, $"scanner_watchlist_{key}.json");
        if (!File.Exists(file))
            return set;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(file));
            if (doc.RootElement.TryGetProperty("pairs", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in arr.EnumerateArray())
                {
                    var s = item.GetString()?.Trim();
                    if (!string.IsNullOrEmpty(s))
                        set.Add(s);
                }
            }
        }
        catch { /* ignore malformed watchlist */ }
        return set;
    }

    public static IReadOnlyList<OpportunityBoardRow> LoadFromResultsDb(
        string lane, string tab, HashSet<string>? watchlist = null)
    {
        if (tab == "logs")
            return Array.Empty<OpportunityBoardRow>();
        var db = ProfilePaths.ResultsDb;
        if (!File.Exists(db))
            return Array.Empty<OpportunityBoardRow>();
        var reader = new ResultsDbReader(db);
        var runId = reader.LatestRunId("lane_scan", lane)
            ?? reader.LatestRunId("migrate_opportunity", lane)
            ?? reader.LatestRunId("opportunity", lane);
        if (runId is null)
            return Array.Empty<OpportunityBoardRow>();

        var list = new List<OpportunityBoardRow>();
        using var conn = new SqliteConnection($"Data Source={db}");
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText =
            "SELECT pair, payload_json FROM opportunity_rows WHERE run_id=$run ORDER BY row_id";
        cmd.Parameters.AddWithValue("$run", runId);
        using var rdr = cmd.ExecuteReader();
        while (rdr.Read())
        {
            var pair = rdr.GetString(0);
            var payload = rdr.IsDBNull(1) ? "{}" : rdr.GetString(1);
            using var doc = JsonDocument.Parse(payload);
            var row = doc.RootElement;
            var watch = (row.TryGetProperty("watch", out var w) && w.ValueKind == JsonValueKind.True)
                || (watchlist is not null && watchlist.Contains(pair));
            if (tab == "watchlist" && !watch)
                continue;
            list.Add(FromPayload(row, pair, payload, watch, lane));
        }
        return list;
    }

    private static IReadOnlyList<OpportunityBoardRow> LoadFromLtsJson(
        string lane, string tab, HashSet<string>? watchlist = null)
    {
        var path = BoardPath(lane);
        if (!File.Exists(path))
            return Array.Empty<OpportunityBoardRow>();
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var root = doc.RootElement;
        JsonElement rowsEl;
        if (root.ValueKind == JsonValueKind.Array)
            rowsEl = root;
        else if (root.TryGetProperty("rows", out var r))
            rowsEl = r;
        else
            return Array.Empty<OpportunityBoardRow>();

        var list = new List<OpportunityBoardRow>();
        foreach (var row in rowsEl.EnumerateArray())
        {
            var pair = Str(row, "pair");
            var watch = (row.TryGetProperty("watch", out var w) && w.ValueKind == JsonValueKind.True)
                || (watchlist is not null && watchlist.Contains(pair));
            if (tab == "watchlist" && !watch)
                continue;
            if (tab == "logs")
                continue;
            list.Add(FromPayload(row, pair, row.GetRawText(), watch, lane));
        }
        return list;
    }

    private static OpportunityBoardRow FromPayload(
        JsonElement row, string pairFallback, string payload, bool watch, string lane)
    {
        var pair = string.IsNullOrEmpty(Str(row, "pair")) ? pairFallback : Str(row, "pair");
        var name = Str(row, "name", "symbol");
        if (string.IsNullOrWhiteSpace(name))
            name = pair;
        var gain = Num(row, "gain", "gain_pct", "change_24h");
        var spark7 = NumArray(row, "spark_closes_7d", "closes_7d");
        var spark30 = NumArray(row, "spark_closes_30d", "closes_30d");
        var gain7 = OptNum(row, "gain_7d_pct", "gain_7d", "change_7d")
            ?? PctFromSpark(spark7)
            ?? (gain != 0 ? gain : 0);
        var gain30 = OptNum(row, "gain_30d_pct", "gain_30d", "change_30d")
            ?? PctFromSpark(spark30)
            ?? 0;
        var vol = Num(row, "volume_24h", "volume_score", "vol_score");
        var symbol = Str(row, "symbol");
        var logoKey = FirstNonEmpty(symbol, pair, name);
        Avalonia.Media.Imaging.Bitmap? logoImage = null;
        foreach (var candidate in new[] { logoKey, pair, symbol, name }.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(candidate))
                continue;
            logoImage = CoinIconResolver.Load(candidate, lane);
            if (logoImage is not null)
                break;
        }
        var taBest = Num(row, "bot_best_net_pct", "best_bt_pct", "best_net_pct");
        var taLabel = FirstNonEmpty(Str(row, "bot_best_label", "bot_best_name"), "");
        var (bestBt, bestLabel) = PreferBuyHoldWhenBetter(row, taBest, taLabel);
        var volAccel = OptNum(row, "volume_acceleration_pct", "vol_delta_pct", "volume_delta_pct");
        var exchange = Str(row, "exchange", "exchange_id");
        var volumeUnit = Str(row, "volume_unit");
        return new OpportunityBoardRow
        {
            Watch = watch,
            Logo = CoinIconResolver.LogoGlyph(logoKey),
            LogoImage = logoImage,
            Name = name,
            Pair = pair,
            Gain7d = gain7,
            Spark7d = "spark",
            SparkCloses7d = spark7,
            Gain30d = gain30,
            Spark30d = "spark",
            SparkCloses30d = spark30,
            BestBtPct = bestBt,
            BotVsBhPct = OptNum(row, "bot_vs_bh_pct"),
            Health = FirstNonEmpty(Str(row, "health", "grade"), HealthLabel(row)),
            HealthScore = OptNum(row, "health_score"),
            ChartDist7dPct = OptNum(row, "chart_dist_7d_pct") ?? DistFromHigh(spark7),
            ChartDist30dPct = OptNum(row, "chart_dist_30d_pct") ?? DistFromHigh(spark30),
            VolumeAccelPct = volAccel,
            Hv7d = Num(row, "hv_7d_pct", "hv_7d"),
            MaxDd = Num(row, "max_drawdown_pct", "max_dd_pct", "max_dd"),
            VolDelta = volAccel ?? 0,
            Exchange = exchange,
            VolumeUnit = volumeUnit,
            Volume24h = vol,
            Events = FirstNonEmpty(Str(row, "events_label", "events"), "·"),
            Backtest = bestBt != 0 || !string.IsNullOrWhiteSpace(bestLabel) ? "Results" : "—",
            BotBestLabel = bestLabel,
            Gain = gain7 != 0 ? gain7 : gain,
            VolumeScore = vol,
            OhlcvSource = Str(row, "ohlcv_source", "bar_source"),
            Regime = Str(row, "regime", "market_regime"),
            Score = Num(row, "score", "ta_score", "rank_score"),
            Price = Num(row, "price", "last", "last_price"),
            Heat = HeatLabel(gain7 != 0 ? gain7 : gain, Str(row, "heat", "heat_band")),
            PayloadJson = payload,
        };
    }

    /// <summary>When B&amp;H net beats every TA strategy, show B&amp;H as Best BT / Best TA.</summary>
    private static (double BestBt, string BestLabel) PreferBuyHoldWhenBetter(
        JsonElement row, double taBest, string taLabel)
    {
        var bhNet = OptNum(row, "buy_hold_net_pct");
        if (bhNet is not { } bh || bh <= taBest + 1e-12)
            return (taBest, taLabel);
        var bhTf = "";
        if (row.TryGetProperty("backtest_buy_hold", out var nested)
            && nested.ValueKind == JsonValueKind.Object)
            bhTf = Str(nested, "timeframe", "tf");
        var label = string.IsNullOrWhiteSpace(bhTf) ? "B&H" : $"{bhTf} B&H";
        return (bh, label);
    }

    private static double? PctFromSpark(IReadOnlyList<double> closes)
    {
        if (closes.Count < 2)
            return null;
        var first = closes[0];
        var last = closes[^1];
        if (first == 0 || double.IsNaN(first) || double.IsNaN(last))
            return null;
        return (last / first - 1.0) * 100.0;
    }

    private static double? DistFromHigh(IReadOnlyList<double> closes)
    {
        if (closes.Count < 2)
            return null;
        var high = closes.Max();
        var last = closes[^1];
        if (high <= 0 || double.IsNaN(high) || double.IsNaN(last))
            return null;
        return (high - last) / high * 100.0;
    }

    private static string HeatLabel(double gain, string explicitHeat)
    {
        if (!string.IsNullOrWhiteSpace(explicitHeat))
            return explicitHeat;
        if (gain >= 8)
            return "hot";
        if (gain >= 2)
            return "warm";
        if (gain <= -5)
            return "cold";
        return "flat";
    }

    private static string BoardPath(string lane)
    {
        var root = ProfilePaths.DeviceRoot;
        var key = (lane ?? "crypto").Trim().ToLowerInvariant();
        return key is "" or "crypto"
            ? Path.Combine(root, "lts_scan_rows.json")
            : Path.Combine(root, $"lts_scan_rows_{key}.json");
    }

    private static string FirstNonEmpty(params string[] values)
    {
        foreach (var value in values)
        {
            if (!string.IsNullOrWhiteSpace(value))
                return value;
        }
        return "";
    }

    private static string HealthLabel(JsonElement row)
    {
        var score = OptNum(row, "health_score");
        return score is null
            ? ""
            : ((int)score.Value).ToString(CultureInfo.InvariantCulture);
    }

    private static string Str(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (row.TryGetProperty(k, out var p) && p.ValueKind == JsonValueKind.String)
                return p.GetString() ?? "";
        }
        return "";
    }

    private static double Num(JsonElement row, params string[] keys) =>
        OptNum(row, keys) ?? 0;

    private static IReadOnlyList<double> NumArray(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (!row.TryGetProperty(k, out var p) || p.ValueKind != JsonValueKind.Array)
                continue;
            var list = new List<double>();
            foreach (var item in p.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.Number)
                    continue;
                if (item.TryGetDouble(out var v) && !double.IsNaN(v))
                    list.Add(v);
            }
            if (list.Count > 0)
                return list;
        }
        return Array.Empty<double>();
    }

    private static double? OptNum(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (!row.TryGetProperty(k, out var p))
                continue;
            if (p.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined or JsonValueKind.String)
            {
                if (p.ValueKind == JsonValueKind.String
                    && double.TryParse(p.GetString(), System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out var parsed))
                    return parsed;
                continue;
            }
            if (p.ValueKind == JsonValueKind.Number && p.TryGetDouble(out var v))
                return v;
        }
        return null;
    }
}
