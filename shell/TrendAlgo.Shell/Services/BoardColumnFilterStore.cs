using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public static class BoardColumnFilterStore
{
    public static string FiltersPath =>
        Path.Combine(ProfilePaths.DeviceRoot, "scanner_filters.json");

    public static void Load(BoardColumnFilterState state, string? path = null)
    {
        var file = path ?? FiltersPath;
        if (!File.Exists(file))
            return;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(file));
            var root = doc.RootElement;
            state.MinGain7dText = FloorText(root, "min_gain_7d");
            state.MinGain30dText = root.TryGetProperty("min_gain_30d", out _)
                ? FloorText(root, "min_gain_30d")
                : FloorText(root, "min_gain_pct");
            state.MinBestBtText = FloorText(root, "min_best_bt");
            state.HealthMinText = FloorText(root, "health_min");
            state.BotVsBh = Str(root, "bot_vs_bh_filter");
            state.ChartDistMax7d = Str(root, "chart_dist_max_7d");
            state.ChartDistMax30d = Str(root, "chart_dist_max_30d");
            state.VolAccel = Str(root, "vol_accel_filter");
            state.Vol24Min = Str(root, "vol24_min");
            if (root.TryGetProperty("view_exchanges", out var arr) && arr.ValueKind == JsonValueKind.Array)
                state.ExchangeText = string.Join(',', arr.EnumerateArray().Select(e => e.ToString()));
            state.SyncOptionsFromValues();
        }
        catch
        {
            /* leave defaults */
        }
    }

    public static void Save(BoardColumnFilterState state, string? path = null)
    {
        var file = path ?? FiltersPath;
        JsonObject obj;
        try
        {
            obj = File.Exists(file)
                ? JsonNode.Parse(File.ReadAllText(file)) as JsonObject ?? new JsonObject()
                : new JsonObject();
        }
        catch
        {
            obj = new JsonObject();
        }

        void SetFloor(string key, double? v) =>
            obj[key] = v is null ? null : JsonValue.Create(v.Value);

        SetFloor("min_gain_7d", state.MinGain7d);
        SetFloor("min_gain_30d", state.MinGain30d);
        SetFloor("min_gain_pct", state.MinGain30d);
        SetFloor("min_best_bt", state.MinBestBt);
        obj["health_min"] = state.HealthMin is null
            ? ""
            : state.HealthMin.Value.ToString(CultureInfo.InvariantCulture);
        obj["bot_vs_bh_filter"] = state.BotVsBh;
        obj["chart_dist_max_7d"] = state.ChartDistMax7d;
        obj["chart_dist_max_30d"] = state.ChartDistMax30d;
        obj["vol_accel_filter"] = state.VolAccel;
        obj["vol24_min"] = state.Vol24Min;
        var ex = state.ViewExchanges;
        if (ex is null)
            obj.Remove("view_exchanges");
        else
        {
            var ja = new JsonArray();
            foreach (var id in ex)
                ja.Add(id);
            obj["view_exchanges"] = ja;
        }

        var dir = Path.GetDirectoryName(file);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        File.WriteAllText(file, JsonNodeWrite.ToIndented(obj));
    }

    private static string FloorText(JsonElement root, string key)
    {
        if (!root.TryGetProperty(key, out var p) || p.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
            return "";
        if (p.ValueKind == JsonValueKind.String)
        {
            var s = p.GetString() ?? "";
            return string.IsNullOrWhiteSpace(s) ? "" : s.Trim();
        }
        return p.TryGetDouble(out var v) ? ((int)v).ToString(CultureInfo.InvariantCulture) : "";
    }

    private static string Str(JsonElement root, string key) =>
        root.TryGetProperty(key, out var p) && p.ValueKind != JsonValueKind.Null
            ? p.ToString()
            : "";
}
