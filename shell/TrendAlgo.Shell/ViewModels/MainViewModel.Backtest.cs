using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private bool _suppressBacktestPrefsPersist;
    private bool _backtestFiltersHydrated;
    private CancellationTokenSource? _backtestCts;
    private Process? _backtestProc;

    public event Action<JsonElement?>? BacktestMarketContextUpdated;
    public JsonElement? BacktestMarketContextJson { get; private set; }
    public ObservableCollection<StrategyResultRow> BacktestResultRows { get; } = new();

    [ObservableProperty] private StrategyResultRow? _selectedBacktestResultRow;
    [ObservableProperty] private string _backtestNoteText = "";
    [ObservableProperty] private string _backtestMcSignal = "Run a scan with candles to fill Market Context.";
    [ObservableProperty] private string _backtestMcLevels = "—";
    [ObservableProperty] private string _backtestMcRisk = "—";
    [ObservableProperty] private string _backtestMcStructure = "—";

    public bool BacktestMarketCtxExpanded
    {
        get => !BacktestMarketCtxCollapsed;
        set
        {
            if (BacktestMarketCtxCollapsed == !value)
                return;
            BacktestMarketCtxCollapsed = !value;
            OnPropertyChanged();
            if (!_suppressBacktestPrefsPersist && ShowBacktestStrip)
                PersistBacktestPrefs();
        }
    }

    partial void OnBacktestMarketCtxCollapsedChanged(bool value) =>
        OnPropertyChanged(nameof(BacktestMarketCtxExpanded));

    [RelayCommand]
    private void BacktestReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("backtest", "crypto", BacktestPair);
            var root = doc.RootElement;
            if (root.TryGetProperty("pair", out var p) && p.GetString() is { Length: > 0 } pair)
                BacktestPair = pair;
            else if (string.IsNullOrWhiteSpace(BacktestPair)
                     && root.TryGetProperty("last_pair", out var lp)
                     && lp.GetString() is { Length: > 0 } last)
                BacktestPair = last;

            if (root.TryGetProperty("run_label", out var rl))
                BacktestRunLabel = rl.ToString();
            if (root.TryGetProperty("refresh_label", out var rfl))
                BacktestRefreshLabel = rfl.ToString();
            if (root.TryGetProperty("status_label", out var sl))
                BacktestStatusLabel = sl.ToString();
            if (root.TryGetProperty("perfect_label", out var pl))
                BacktestPerfectLabel = pl.ToString();
            if (root.TryGetProperty("empty_title", out var et))
                BacktestEmptyTitle = et.ToString();
            if (root.TryGetProperty("empty_body", out var eb))
                BacktestEmptyBody = eb.ToString();
            if (root.TryGetProperty("strategy_caption", out var sc))
                BacktestStrategyCaption = sc.ToString();
            _suppressBacktestPrefsPersist = true;
            BacktestPerfectOnly = root.TryGetProperty("perfect_only", out var po)
                && po.ValueKind == JsonValueKind.True;
            BacktestMarketCtxCollapsed = root.TryGetProperty("market_context_collapsed", out var mcc)
                && mcc.ValueKind == JsonValueKind.True;
            _suppressBacktestPrefsPersist = false;

            if (!_backtestFiltersHydrated
                && root.TryGetProperty("filters", out var initFl)
                && initFl.ValueKind == JsonValueKind.Object)
            {
                HydrateBacktestFilters(initFl);
                _backtestFiltersHydrated = true;
            }
            else
            {
                _backtestFiltersHydrated = true;
            }

            StrategyRows.Clear();
            BacktestResultRows.Clear();
            var mapped = new List<StrategyResultRow>();
            if (root.TryGetProperty("rows", out var rows) && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    var id = r.TryGetProperty("indicator", out var ind) ? ind.ToString() : "row";
                    var pairCell = r.TryGetProperty("pair", out var pr) ? pr.ToString() : BacktestPair;
                    StrategyRows.Add(new StrategyRow(id, pairCell, r.GetRawText()));
                    mapped.Add(StrategyResultMapper.FromJson(r));
                }
            }
            StrategyResultMapper.ApplyHeat(mapped);
            foreach (var row in mapped)
                BacktestResultRows.Add(row);

            if (root.TryGetProperty("market_context_summary", out var sum)
                && sum.ValueKind == JsonValueKind.Object)
            {
                var sig = SummaryStr(sum, "signal");
                var lvl = SummaryStr(sum, "levels");
                var rsk = SummaryStr(sum, "risk");
                var str = SummaryStr(sum, "structure");
                BacktestMcSignal = string.IsNullOrWhiteSpace(sig)
                    ? "Run a scan with candles to fill Market Context."
                    : sig;
                BacktestMcLevels = string.IsNullOrWhiteSpace(lvl) ? "—" : lvl;
                BacktestMcRisk = string.IsNullOrWhiteSpace(rsk) ? "—" : rsk;
                BacktestMcStructure = string.IsNullOrWhiteSpace(str) ? "—" : str;
            }
            else
            {
                BacktestMcSignal = "Run a scan with candles to fill Market Context.";
                BacktestMcLevels = "—";
                BacktestMcRisk = "—";
                BacktestMcStructure = "—";
            }

            if (root.TryGetProperty("market_context", out var mc)
                && mc.ValueKind == JsonValueKind.Object
                && mc.EnumerateObject().Any())
            {
                BacktestMarketContextJson = mc.Clone();
            }
            else
            {
                BacktestMarketContextJson = null;
            }
            BacktestMarketContextUpdated?.Invoke(BacktestMarketContextJson);
            MarketContextText = BacktestMcSignal;

            var rawCount = root.TryGetProperty("raw_count", out var rawEl)
                && rawEl.TryGetInt32(out var rcVal)
                ? rcVal
                : mapped.Count;
            RowCount = mapped.Count;
            BacktestEmpty = rawCount == 0 && mapped.Count == 0;
            ShowWorkbook = false;
            BacktestNoteText = BacktestEmpty
                ? ""
                : mapped.Count < rawCount
                    ? $"{mapped.Count} of {rawCount} strategies · Oracle/B&H pinned (filters applied)"
                    : $"{mapped.Count} strategies · Oracle/B&H pinned";
            OnPropertyChanged(nameof(ShowBacktestColumnFilters));
            var filterNote = root.TryGetProperty("filters", out var fl)
                && fl.ValueKind == JsonValueKind.Object
                && fl.EnumerateObject().Any()
                ? " (filtered)"
                : "";
            StatusText = BacktestEmpty
                ? $"Backtest · {BacktestEmptyTitle}"
                : $"Backtest {BacktestPair}: {RowCount} strategies{filterNote}";
        }
        catch (Exception ex)
        {
            StatusText = $"Backtest reload failed: {ex.Message}";
        }
    }

    private void HydrateBacktestFilters(JsonElement fl)
    {
        static string GetStr(JsonElement obj, string key) =>
            obj.TryGetProperty(key, out var v) && v.ValueKind != JsonValueKind.Null ? v.ToString() : "";

        BacktestFilters.IndicatorContains = GetStr(fl, "indicator_contains");
        BacktestFilters.Timeframe = GetStr(fl, "timeframe");
        BacktestFilters.ParamsContains = GetStr(fl, "params_contains");
        BacktestFilters.MinNetPct = GetStr(fl, "min_net_pct");
        BacktestFilters.MaxFees = GetStr(fl, "max_fees");
        BacktestFilters.MaxOpen = GetStr(fl, "max_open");
        BacktestFilters.MinWins = GetStr(fl, "min_wins");
        BacktestFilters.MaxLosses = GetStr(fl, "max_losses");
        BacktestFilters.MinWinPct = GetStr(fl, "min_win_pct");
        BacktestFilters.MaxTslPct = GetStr(fl, "max_tsl_pct");
        BacktestFilters.MaxTslHits = GetStr(fl, "max_tsl_hits");
        BacktestFilters.MaxTslHitPct = GetStr(fl, "max_tsl_hit_pct");
        BacktestFilters.MinStrength = GetStr(fl, "min_strength");
    }

    private static string SummaryStr(JsonElement obj, string key) =>
        obj.TryGetProperty(key, out var p) && p.ValueKind != JsonValueKind.Null ? p.ToString() : "";

    [RelayCommand]
    private void ApplyBacktestColumnFilters()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_backtest_filters.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, BacktestFilters.ToJsonObject());
            BacktestReload();
            StatusText = $"Backtest filters applied · {RowCount} rows";
        }
        catch (Exception ex)
        {
            StatusText = $"Backtest filters failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void ClearBacktestColumnFilters()
    {
        BacktestFilters.IndicatorContains = "";
        BacktestFilters.Timeframe = "";
        BacktestFilters.ParamsContains = "";
        BacktestFilters.MinNetPct = "";
        BacktestFilters.MaxFees = "";
        BacktestFilters.MaxOpen = "";
        BacktestFilters.MinWins = "";
        BacktestFilters.MaxLosses = "";
        BacktestFilters.MinWinPct = "";
        BacktestFilters.MaxTslPct = "";
        BacktestFilters.MaxTslHits = "";
        BacktestFilters.MaxTslHitPct = "";
        BacktestFilters.MinStrength = "";
        ApplyBacktestColumnFilters();
    }

    [RelayCommand]
    private async Task BacktestRun()
    {
        var targetPair = (BacktestPair ?? "").Trim().ToUpperInvariant();
        if (string.IsNullOrWhiteSpace(targetPair))
            targetPair = FirstBoardPair();
        if (string.IsNullOrWhiteSpace(targetPair))
            targetPair = "BTC/USD";
        if (!targetPair.Contains('/', StringComparison.Ordinal))
            targetPair = $"{targetPair}/USD";
        BacktestPair = targetPair;
        PersistBacktestPrefs();

        _backtestCts?.Cancel();
        _backtestCts = new CancellationTokenSource();
        var ct = _backtestCts.Token;

        try
        {
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.Delete(Path.Combine(ProfilePaths.DeviceRoot, "pair_backtest_cancel.flag"));
            var seed = new JsonObject
            {
                ["current_pair"] = targetPair,
                ["phase"] = "start",
                ["done"] = 0,
                ["total"] = 100,
                ["pairs_done"] = 0,
                ["pairs_total"] = 1,
                ["message"] = $"Starting isolated All-TA backtest for {targetPair}…",
                ["events"] = new JsonArray($"Starting isolated All-TA backtest for {targetPair}…"),
            };
            File.WriteAllText(
                Path.Combine(ProfilePaths.DeviceRoot, "pair_strategy_scan_progress.json"),
                JsonNodeWrite.ToIndented(seed));
        }
        catch { /* best-effort seed */ }

        await OpenScanProgressFor("backtest");
        StatusText = $"Running All-TA backtest for {targetPair}…";
        try
        {
            using var doc = await _surfaces.RunPairBacktestAsync(
                targetPair, "crypto", p => _backtestProc = p, ct);
            _backtestProc = null;
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var okEl) && okEl.ValueKind == JsonValueKind.True;
            var cancelled = root.TryGetProperty("cancelled", out var ce) && ce.ValueKind == JsonValueKind.True;
            BacktestPair = targetPair;
            BacktestReload();
            if (cancelled)
                StatusText = $"Backtest cancelled ({targetPair})";
            else if (!ok)
            {
                var err = root.TryGetProperty("error", out var ee) ? ee.ToString() : "backtest failed";
                StatusText = $"Backtest failed ({targetPair}): {err}";
            }
        }
        catch (Exception ex)
        {
            _backtestProc = null;
            StatusText = $"Backtest failed ({targetPair}): {ex.Message}";
        }
    }

    [RelayCommand]
    private void BacktestRefreshPrices()
    {
        EnqueueDesk("refresh_prices", busy: true);
        StatusText = "Refresh prices enqueued";
    }

    partial void OnBacktestPerfectOnlyChanged(bool value)
    {
        if (_suppressBacktestPrefsPersist || !ShowBacktestStrip)
            return;
        PersistBacktestPrefs();
        BacktestReload();
    }

    [RelayCommand]
    private void BacktestToggleMarketCtx()
    {
        BacktestMarketCtxCollapsed = !BacktestMarketCtxCollapsed;
        PersistBacktestPrefs();
        StatusText = BacktestMarketCtxCollapsed
            ? "Market context collapsed"
            : "Market context expanded";
    }

    private void PersistBacktestPrefs()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_results_prefs.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var pair = EscapeJson(BacktestPair ?? "BTC/USD");
            File.WriteAllText(path,
                "{"
                + $"\"perfect_only\":{(BacktestPerfectOnly ? "true" : "false")},"
                + $"\"market_context_collapsed\":{(BacktestMarketCtxCollapsed ? "true" : "false")},"
                + $"\"last_pair\":\"{pair}\""
                + "}");
            using var doc = _surfaces.ApplyResultsPrefs(path);
            _ = doc;
        }
        catch
        {
            /* non-fatal */
        }
    }

    [RelayCommand]
    private void BacktestDeriveOracle()
    {
        var pair = string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair;
        if (string.IsNullOrWhiteSpace(pair))
            pair = "BTC/USD";
        try
        {
            using var doc = _surfaces.DeriveOracle(DeskLane(), pair);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var msg = doc.RootElement.TryGetProperty("message", out var m) ? m.ToString() : "No sauce preference";
                StatusText = msg;
                return;
            }
            if (doc.RootElement.TryGetProperty("prefill", out var pre) && pre.ValueKind == JsonValueKind.Object)
            {
                PlanDraftName = pre.TryGetProperty("name", out var n) ? n.ToString() : PlanDraftName;
                PlanDraftPair = pre.TryGetProperty("pair", out var p) ? p.ToString() : pair;
                PlanDraftStrategy = pre.TryGetProperty("strategy", out var s) ? s.ToString() : PlanDraftStrategy;
                PlanDraftTimeframe = pre.TryGetProperty("timeframe", out var t) ? t.ToString() : PlanDraftTimeframe;
            }
            var note = doc.RootElement.TryGetProperty("message", out var mm) ? mm.ToString() : "Derived";
            BotsPrefillNote = note;
            StatusText = note + " — open Bots to Save plan draft / Send to host";
            Navigate("bots");
        }
        catch (Exception ex)
        {
            StatusText = $"Derive Oracle failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BacktestCreateBot()
    {
        var pair = string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair;
        if (string.IsNullOrWhiteSpace(pair))
        {
            StatusText = "Set a backtest pair first";
            return;
        }
        var picked = SelectedBacktestResultRow is { CanCreateBot: true }
            ? SelectedBacktestResultRow
            : BacktestResultRows.FirstOrDefault(r => r.CanCreateBot);
        var indicator = picked?.Indicator ?? StrategyRows.FirstOrDefault()?.StrategyId ?? "RSI";
        var clean = CleanIndicatorName(indicator);
        if (string.IsNullOrWhiteSpace(clean) || clean is "B&H" or "Oracle max")
            clean = "RSI";
        CreateBotForPairAndIndicator(pair, clean, "backtest");
    }

    public void BacktestCreateBotForResultRow(StrategyResultRow? row)
    {
        if (row is not { CanCreateBot: true })
        {
            StatusText = "Pick a strategy row (not Oracle / B&H) to create a bot.";
            return;
        }
        var clean = CleanIndicatorName(row.Indicator);
        if (string.IsNullOrWhiteSpace(clean))
        {
            StatusText = "Pick a strategy row (not Oracle / B&H) to create a bot.";
            return;
        }
        var pair = string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair;
        if (string.IsNullOrWhiteSpace(pair))
            pair = "BTC/USD";
        CreateBotForPairAndIndicator(pair, clean, "backtest");
    }

    [RelayCommand]
    private void BacktestCreateBotForRow(StrategyRow? row)
    {
        if (row is null)
            return;
        if (row.StrategyId.StartsWith("Oracle", StringComparison.OrdinalIgnoreCase)
            || row.StrategyId.StartsWith("B&H", StringComparison.Ordinal))
        {
            StatusText = "Pick a strategy row (not Oracle / B&H) to create a bot.";
            return;
        }
        var pair = string.IsNullOrWhiteSpace(row.Pair) ? BacktestPair : row.Pair;
        CreateBotForPairAndIndicator(pair, row.StrategyId, "backtest");
    }

    private static string CleanIndicatorName(string raw)
    {
        var clean = (raw ?? "").Split('—')[0].Split('←')[0].Trim();
        if (clean.EndsWith(" *", StringComparison.Ordinal))
            clean = clean[..^2].Trim();
        return clean;
    }

    private void CreateBotForPairAndIndicator(string pair, string indicator, string source)
    {
        try
        {
            using var created = _surfaces.CreateBot(pair, indicator);
            var name = created.RootElement.TryGetProperty("name", out var n) ? n.ToString() : pair;
            BotsPrefillNote = $"Prefill from {source} · {name} ({pair} · {indicator})";
            StatusText = BotsPrefillNote;
            Navigate("bots");
        }
        catch (Exception ex)
        {
            StatusText = $"Create Bot failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task BacktestOpenGlossary()
    {
        var term = SelectedBacktestResultRow?.Indicator
            ?? BacktestResultRows.FirstOrDefault(r => r.CanCreateBot)?.Indicator
            ?? (StrategyRows.Count > 0 ? StrategyRows[0].StrategyId : "");
        if (string.IsNullOrWhiteSpace(term) && !string.IsNullOrWhiteSpace(BacktestPair))
            term = BacktestPair.Split('/')[0];
        var clean = CleanIndicatorName(term);
        GlossaryQuery = clean;
        try
        {
            using var doc = new DeskSurfaceClient().Fetch("glossary", DeskLane(), clean);
            var popup = new GlossaryPopupWindow();
            DeskSurfacePresenter.BindGlossaryPopup(popup, doc.RootElement, clean);
            if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
                {
                    MainWindow: { } owner
                })
                await popup.ShowDialog(owner);
            else
                popup.Show();
        }
        catch (Exception ex)
        {
            StatusText = $"Glossary failed: {ex.Message}";
            Navigate("glossary");
        }
    }

    [RelayCommand]
    private void BacktestCancel()
    {
        try
        {
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(Path.Combine(ProfilePaths.DeviceRoot, "pair_backtest_cancel.flag"), "1");
        }
        catch { /* ignore */ }
        try { _backtestCts?.Cancel(); } catch { /* ignore */ }
        try
        {
            if (_backtestProc is { HasExited: false })
                _backtestProc.Kill(entireProcessTree: true);
        }
        catch { /* ignore */ }
        EnqueueDesk("cancel_backtest", busy: false);
        StatusText = $"Cancelling backtest ({BacktestPair})…";
    }

    [RelayCommand]
    private async Task BacktestOpenResults() =>
        await OpenSurfaceAsync("results", string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair);

    [RelayCommand]
    private async Task BacktestOpenSauce() =>
        await OpenSurfaceAsync("sauce", BacktestPair);

    [RelayCommand]
    private async Task BacktestOpenChart() =>
        await BacktestOpenChartWindowAsync("30d");

    [RelayCommand]
    private async Task BacktestOpenChart7d() =>
        await BacktestOpenChartWindowAsync("7d");

    [RelayCommand]
    private async Task BacktestOpenChart30d() =>
        await BacktestOpenChartWindowAsync("30d");

    private async Task BacktestOpenChartWindowAsync(string windowKey)
    {
        var pair = string.IsNullOrWhiteSpace(BacktestPair) ? FirstBoardPair() : BacktestPair;
        if (string.IsNullOrWhiteSpace(pair))
            pair = "BTC/USD";
        await OpenSurfaceAsync("chart", $"{pair}|{windowKey}");
    }

    [RelayCommand]
    private async Task BacktestOpenEvents() =>
        await OpenSurfaceAsync("events", string.IsNullOrWhiteSpace(BacktestPair) ? "BTC/USD" : BacktestPair);

    [RelayCommand]
    private async Task BacktestOpenSettings()
    {
        try
        {
            if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
                {
                    MainWindow: { } owner
                })
            {
                StatusText = "Loading scan settings…";
                var dlg = await LoadingWindow.RunAsync(
                    owner, "Loading scan settings…", ScanSettingsWindow.CreateLoadedAsync);
                var saved = await dlg.ShowDialog<bool?>(owner);
                StatusText = saved == true
                    ? "Backtest settings saved"
                    : "Backtest settings closed";
            }
        }
        catch (Exception ex)
        {
            StatusText = $"Backtest settings failed: {ex.Message}";
        }
    }
}
