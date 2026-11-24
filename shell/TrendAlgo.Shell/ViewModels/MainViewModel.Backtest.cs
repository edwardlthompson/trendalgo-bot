using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Nodes;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private bool _suppressBacktestPrefsPersist;
    private CancellationTokenSource? _backtestCts;
    private Process? _backtestProc;

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
            BacktestEmpty = root.TryGetProperty("empty", out var empty)
                && empty.ValueKind == JsonValueKind.True;

            StrategyRows.Clear();
            if (root.TryGetProperty("rows", out var rows) && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    var id = r.TryGetProperty("indicator", out var ind) ? ind.ToString() : "row";
                    var pairCell = r.TryGetProperty("pair", out var pr) ? pr.ToString() : BacktestPair;
                    StrategyRows.Add(new StrategyRow(id, pairCell, r.GetRawText()));
                }
            }
            if (root.TryGetProperty("market_context", out var mc)
                && mc.ValueKind == JsonValueKind.Object)
            {
                var bits = new List<string>();
                foreach (var prop in mc.EnumerateObject().Take(12))
                    bits.Add($"{prop.Name}: {prop.Value}");
                MarketContextText = bits.Count == 0
                    ? "(no market context on last backtest)"
                    : string.Join(" · ", bits);
            }
            else
                MarketContextText = "(no market context on last backtest)";
            RowCount = StrategyRows.Count;
            BacktestEmpty = RowCount == 0 && !(root.TryGetProperty("raw_count", out var rc)
                && rc.TryGetInt32(out var raw) && raw > 0);
            // Keep grid visible when filters hide all rows but raw results exist.
            if (root.TryGetProperty("raw_count", out var rawEl)
                && rawEl.TryGetInt32(out var rawCount)
                && rawCount > 0)
                BacktestEmpty = false;
            ShowWorkbook = !BacktestEmpty || StrategyRows.Count > 0;
            OnPropertyChanged(nameof(ShowBacktestColumnFilters));
            var filterNote = root.TryGetProperty("filters", out var fl)
                && fl.ValueKind == JsonValueKind.Object
                && fl.EnumerateObject().Any()
                ? " (filtered)"
                : "";
            StatusText = StrategyRows.Count == 0 && !ShowWorkbook
                ? $"Backtest · {BacktestEmptyTitle}"
                : $"Backtest {BacktestPair}: {RowCount} strategies{filterNote}";
        }
        catch (Exception ex)
        {
            StatusText = $"Backtest reload failed: {ex.Message}";
        }
    }

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
        var indicator = StrategyRows.FirstOrDefault()?.StrategyId ?? "RSI";
        if (indicator is "B&H" or "Oracle max")
            indicator = StrategyRows.Skip(1).FirstOrDefault()?.StrategyId ?? "RSI";
        CreateBotForPairAndIndicator(pair, indicator, "backtest");
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
        var term = StrategyRows.Count > 0 ? StrategyRows[0].StrategyId : "";
        if (string.IsNullOrWhiteSpace(term) && !string.IsNullOrWhiteSpace(BacktestPair))
            term = BacktestPair.Split('/')[0];
        var clean = term.Split('←')[0].Trim();
        if (clean.EndsWith(" *", StringComparison.Ordinal))
            clean = clean[..^2].Trim();
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
        await OpenSurfaceAsync("chart", BacktestPair);

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
