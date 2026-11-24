using System.Globalization;
using System.Text.Json.Nodes;
using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

/// <summary>Per-column board filter chrome — keys match ScannerColumnFilterRow.dump().</summary>
public sealed partial class BoardColumnFilterState : ObservableObject
{
    public static IReadOnlyList<FilterOption> ChartDistOptions { get; } =
    [
        new("", "·"), new("5", "5%"), new("10", "10%"), new("15", "15%"),
    ];

    public static IReadOnlyList<FilterOption> BotVsBhOptions { get; } =
    [
        new("", "·"), new("pos", "Bot+"), new("neg", "B&H+"),
    ];

    public static IReadOnlyList<FilterOption> VolAccelOptions { get; } =
    [
        new("", "·"), new("pos", "+"), new("25", "25%"), new("50", "50%"),
    ];

    public static IReadOnlyList<FilterOption> Vol24Options { get; } =
    [
        new("", "·"), new("100000", "100k"), new("500000", "500k"),
        new("1000000", "1M"), new("10000000", "10M"),
    ];

    [ObservableProperty] private string _minGain7dText = "";
    [ObservableProperty] private string _minGain30dText = "";
    [ObservableProperty] private string _minBestBtText = "";
    [ObservableProperty] private string _healthMinText = "";
    [ObservableProperty] private string _botVsBh = "";
    [ObservableProperty] private string _chartDistMax7d = "";
    [ObservableProperty] private string _chartDistMax30d = "";
    [ObservableProperty] private string _volAccel = "";
    [ObservableProperty] private string _vol24Min = "";
    [ObservableProperty] private string _exchangeText = "";

    [ObservableProperty] private FilterOption? _chartDist7Option;
    [ObservableProperty] private FilterOption? _chartDist30Option;
    [ObservableProperty] private FilterOption? _botVsBhOption;
    [ObservableProperty] private FilterOption? _volAccelOption;
    [ObservableProperty] private FilterOption? _vol24Option;

    public BoardColumnFilterState() => SyncOptionsFromValues();

    public double? MinGain7d => ParseFloor(MinGain7dText);
    public double? MinGain30d => ParseFloor(MinGain30dText);
    public double? MinBestBt => ParseFloor(MinBestBtText);
    public double? HealthMin => ParseFloor(HealthMinText);
    public double? ChartDistMax7dValue => ParseOptDouble(ChartDistMax7d);
    public double? ChartDistMax30dValue => ParseOptDouble(ChartDistMax30d);
    public double? Vol24MinValue => ParseOptDouble(Vol24Min);

    public IReadOnlyList<string>? ViewExchanges
    {
        get
        {
            var raw = ExchangeText.Trim();
            if (raw.Length == 0)
                return null;
            return raw.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                .Select(s => s.ToLowerInvariant())
                .ToList();
        }
    }

    public void SyncOptionsFromValues()
    {
        ChartDist7Option = Pick(ChartDistOptions, ChartDistMax7d);
        ChartDist30Option = Pick(ChartDistOptions, ChartDistMax30d);
        BotVsBhOption = Pick(BotVsBhOptions, BotVsBh);
        VolAccelOption = Pick(VolAccelOptions, VolAccel);
        Vol24Option = Pick(Vol24Options, Vol24Min);
    }

    partial void OnChartDist7OptionChanged(FilterOption? value)
    {
        if (value is not null)
            ChartDistMax7d = value.Value;
    }

    partial void OnChartDist30OptionChanged(FilterOption? value)
    {
        if (value is not null)
            ChartDistMax30d = value.Value;
    }

    partial void OnBotVsBhOptionChanged(FilterOption? value)
    {
        if (value is not null)
            BotVsBh = value.Value;
    }

    partial void OnVolAccelOptionChanged(FilterOption? value)
    {
        if (value is not null)
            VolAccel = value.Value;
    }

    partial void OnVol24OptionChanged(FilterOption? value)
    {
        if (value is not null)
            Vol24Min = value.Value;
    }

    private static FilterOption Pick(IReadOnlyList<FilterOption> opts, string value) =>
        opts.FirstOrDefault(o => o.Value == value) ?? opts[0];

    private static double? ParseFloor(string text)
    {
        var t = text.Trim();
        if (t.Length == 0)
            return null;
        return double.TryParse(t, NumberStyles.Float, CultureInfo.InvariantCulture, out var v)
            ? v
            : null;
    }

    private static double? ParseOptDouble(string text)
    {
        var t = text.Trim();
        if (t.Length == 0)
            return null;
        return double.TryParse(t, NumberStyles.Float, CultureInfo.InvariantCulture, out var v)
            ? v
            : null;
    }

    /// <summary>Dump active filters for board PNG caption (keys match scanner_filter_summary).</summary>
    public string ToShareFiltersJson(string? pairContains, bool heatmapEnabled, bool buyPicksCollapsed)
    {
        var obj = new JsonObject();
        void Floor(string key, double? v)
        {
            if (v is not null)
                obj[key] = v.Value;
        }

        Floor("min_gain_7d", MinGain7d);
        Floor("min_gain_30d", MinGain30d);
        Floor("min_best_bt", MinBestBt);
        Floor("health_min", HealthMin);
        Floor("chart_dist_max_7d", ChartDistMax7dValue);
        Floor("chart_dist_max_30d", ChartDistMax30dValue);
        Floor("vol24_min", Vol24MinValue);
        if (!string.IsNullOrWhiteSpace(BotVsBh))
            obj["bot_vs_bh_filter"] = BotVsBh;
        if (!string.IsNullOrWhiteSpace(VolAccel))
            obj["vol_accel_filter"] = VolAccel;
        var ex = ViewExchanges;
        if (ex is { Count: > 0 })
        {
            var arr = new JsonArray();
            foreach (var id in ex)
                arr.Add(id);
            obj["view_exchanges"] = arr;
            obj["exchange"] = string.Join(',', ex);
        }
        if (!string.IsNullOrWhiteSpace(pairContains))
            obj["pair_contains"] = pairContains.Trim();
        obj["heatmap_enabled"] = heatmapEnabled;
        obj["buy_picks_collapsed"] = buyPicksCollapsed;
        return Services.JsonNodeWrite.ToCompact(obj);
    }
}
