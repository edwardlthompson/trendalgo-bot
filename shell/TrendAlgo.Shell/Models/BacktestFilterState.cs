using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

/// <summary>Keys match BacktestColumnFilterRow.dump() / backtest_row_filter.filter_rows.</summary>
public sealed partial class BacktestFilterState : ObservableObject
{
    [ObservableProperty] private string _indicatorContains = "";
    [ObservableProperty] private string _timeframe = "";
    [ObservableProperty] private string _paramsContains = "";
    [ObservableProperty] private string _minNetPct = "";
    [ObservableProperty] private string _maxFees = "";
    [ObservableProperty] private string _maxOpen = "";
    [ObservableProperty] private string _minWins = "";
    [ObservableProperty] private string _maxLosses = "";
    [ObservableProperty] private string _minWinPct = "";
    [ObservableProperty] private string _maxTslPct = "";
    [ObservableProperty] private string _maxTslHits = "";
    [ObservableProperty] private string _maxTslHitPct = "";
    [ObservableProperty] private string _minStrength = "";

    public string ToJsonObject()
    {
        var parts = new List<string>();
        void AddStr(string key, string value)
        {
            var v = value?.Trim() ?? "";
            if (v.Length == 0)
                return;
            var esc = v.Replace("\\", "\\\\", StringComparison.Ordinal)
                .Replace("\"", "\\\"", StringComparison.Ordinal);
            parts.Add($"\"{key}\":\"{esc}\"");
        }
        void AddNum(string key, string value, bool allowZero)
        {
            var v = value?.Trim() ?? "";
            if (v.Length == 0)
                return;
            if (!int.TryParse(v, out var n))
                return;
            if (!allowZero && n <= 0)
                return;
            if (!allowZero && n < 0)
                return;
            parts.Add($"\"{key}\":{n}");
        }
        AddStr("indicator_contains", IndicatorContains);
        AddStr("timeframe", Timeframe);
        AddStr("params_contains", ParamsContains);
        AddNum("min_net_pct", MinNetPct, allowZero: false);
        AddNum("max_fees", MaxFees, allowZero: false);
        AddNum("max_open", MaxOpen, allowZero: true);
        AddNum("min_wins", MinWins, allowZero: false);
        AddNum("max_losses", MaxLosses, allowZero: true);
        AddNum("min_win_pct", MinWinPct, allowZero: false);
        AddNum("max_tsl_pct", MaxTslPct, allowZero: false);
        AddNum("max_tsl_hits", MaxTslHits, allowZero: true);
        AddNum("max_tsl_hit_pct", MaxTslHitPct, allowZero: false);
        AddNum("min_strength", MinStrength, allowZero: false);
        return "{" + string.Join(",", parts) + "}";
    }
}
