using System.Text.Json;
using System.Text.Json.Nodes;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private async Task ToggleSelectedWatch()
    {
        var pair = SelectedBoardRow?.Pair ?? FirstBoardPair();
        if (string.IsNullOrWhiteSpace(pair))
        {
            StatusText = "Select a board row to toggle watch";
            return;
        }
        StatusText = $"Updating Watchlist · {pair}…";
        try
        {
            var lane = DeskLane();
            using var doc = await LoadingWindow.RunAsync(
                LoadingWindow.MainOwner(),
                $"Updating Watchlist · {pair}…",
                () => _surfaces.ToggleWatchAsync(lane, pair));
            var watched = doc.RootElement.TryGetProperty("watched", out var w)
                && w.ValueKind == JsonValueKind.True;
            StatusText = watched ? $"Watch on · {pair}" : $"Watch off · {pair}";
            ReloadBoard();
        }
        catch (Exception ex)
        {
            StatusText = $"Watch toggle failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task ToggleWatchForRow(OpportunityBoardRow? row)
    {
        if (row is not null)
            SelectedBoardRow = row;
        await ToggleSelectedWatch();
    }

    private CancellationTokenSource? _buyPicksCts;
    private string _loadedFilterLane = "";

    [ObservableProperty] private int _unfilteredRowCount;
    [ObservableProperty] private bool _hasActiveBoardFilters;

    public string BoardRowsSummaryText => RowCount < UnfilteredRowCount
        ? $"Board rows: {RowCount} / {UnfilteredRowCount} ({UnfilteredRowCount - RowCount} hidden by filters)"
        : $"Board rows: {RowCount}";

    partial void OnBuyPicksExpandedChanged(bool value) => PersistBuyPicksCollapsed(!value);

    private static void PersistBuyPicksCollapsed(bool collapsed)
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "results_view_prefs.json");
            JsonObject root = File.Exists(path)
                ? JsonNode.Parse(File.ReadAllText(path)) as JsonObject ?? new JsonObject()
                : new JsonObject();
            root["buy_picks_collapsed"] = collapsed;
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, JsonNodeWrite.ToIndented(root));
        }
        catch
        {
            /* prefs best-effort */
        }
    }

    private void LoadBuyPicksCollapsedPref()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "results_view_prefs.json");
            if (!File.Exists(path))
                return;
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (doc.RootElement.TryGetProperty("buy_picks_collapsed", out var p)
                && p.ValueKind is JsonValueKind.True or JsonValueKind.False)
            {
                BuyPicksExpanded = p.ValueKind != JsonValueKind.True;
            }
        }
        catch
        {
            /* ignore */
        }
    }

    private void EnsureLaneFiltersLoaded(string lane)
    {
        var key = (lane ?? "crypto").Trim().ToLowerInvariant();
        if (string.Equals(_loadedFilterLane, key, StringComparison.OrdinalIgnoreCase))
            return;
        var prevReady = _filterPersistReady;
        _filterPersistReady = false;
        try
        {
            BoardColumnFilterStore.LoadForLane(QualifiedFilters, key, watchlist: false);
            BoardColumnFilterStore.LoadForLane(WatchlistFilters, key, watchlist: true);
            _loadedFilterLane = key;
        }
        finally
        {
            _filterPersistReady = prevReady;
        }
    }

    [RelayCommand]
    private void ResetBoardFilters()
    {
        var prevReady = _filterPersistReady;
        _filterPersistReady = false;
        try
        {
            BoardFilters.Reset();
            BoardFilter = "";
            BoardColumnFilterStore.SaveForLane(BoardFilters, DeskLane(), BoardTab == "watchlist");
        }
        finally
        {
            _filterPersistReady = prevReady;
        }
        ReloadBoard();
        StatusText = $"Filters cleared → {RowCount} rows";
    }

    private void RefreshBuyPicksFromBoardRows(string lane)
    {
        _buyPicksCts?.Cancel();
        if (BoardTab != "qualified")
        {
            BuyPickRows.Clear();
            ShowBuyPicks = false;
            return;
        }
        var ranked = BuyPicksRanker.FromBoardRows(BoardRows);
        if (ranked.Count > 0 || BoardRows.Count == 0 || BoardRows.Any(r => !string.IsNullOrWhiteSpace(r.PayloadJson)))
        {
            BuyPickRows.Clear();
            foreach (var item in ranked)
                BuyPickRows.Add(item);
            ShowBuyPicks = BuyPickRows.Count > 0;
            return;
        }
        _ = ReloadBuyPicksAsync();
    }

    [RelayCommand]
    private void ReloadBuyPicks() => RefreshBuyPicksFromBoardRows(DeskLane());

    private async Task ReloadBuyPicksAsync()
    {
        _buyPicksCts?.Cancel();
        _buyPicksCts = new CancellationTokenSource();
        var token = _buyPicksCts.Token;
        if (BoardTab != "qualified")
        {
            BuyPickRows.Clear();
            ShowBuyPicks = false;
            return;
        }
        var lane = DeskLane();
        var visible = new HashSet<string>(
            BoardRows.Select(r => r.Pair).Where(p => !string.IsNullOrWhiteSpace(p)),
            StringComparer.OrdinalIgnoreCase);
        try
        {
            var fetched = await Task.Run(() =>
            {
                var items = new List<BuyPickRow>();
                using var doc = _surfaces.Fetch("buy_picks", lane);
                if (doc.RootElement.TryGetProperty("rows", out var rows)
                    && rows.ValueKind == JsonValueKind.Array)
                {
                    foreach (var r in rows.EnumerateArray())
                    {
                        var pair = FirstNonEmpty(S(r, "pair"), S(r, "symbol"));
                        if (visible.Count > 0 && !visible.Contains(pair))
                            continue;
                        items.Add(new BuyPickRow
                        {
                            Pair = pair,
                            Signal = FirstNonEmpty(S(r, "signal"), "Neutral"),
                            Score = D(r, "score"),
                            Confidence = D(r, "confidence"),
                            NearestSr = NullIfEmpty(S(r, "nearest_sr")),
                            RrR1 = OptD(r, "rr_r1"),
                            Confluence = (int)D(r, "confluence"),
                            Regime = NullIfEmpty(S(r, "regime")),
                            BotBestNet = OptD(r, "bot_best_net_pct"),
                            BotBestLabel = NullIfEmpty(S(r, "bot_best_label")),
                        });
                    }
                }
                return items;
            }, token);
            if (token.IsCancellationRequested)
                return;
            Avalonia.Threading.Dispatcher.UIThread.Post(() =>
            {
                if (token.IsCancellationRequested || BoardTab != "qualified")
                    return;
                BuyPickRows.Clear();
                foreach (var item in fetched)
                    BuyPickRows.Add(item);
                ShowBuyPicks = BuyPickRows.Count > 0;
            });
        }
        catch (OperationCanceledException) { /* superseded */ }
        catch
        {
            Avalonia.Threading.Dispatcher.UIThread.Post(() => ShowBuyPicks = false);
        }
    }

    [RelayCommand]
    private void ApplyBoardFilter()
    {
        BoardColumnFilterStore.SaveForLane(BoardFilters, DeskLane(), BoardTab == "watchlist");
        ReloadBoard();
        StatusText = string.IsNullOrWhiteSpace(BoardFilter)
            ? $"Column filters → {RowCount} rows"
            : $"Board filter '{BoardFilter.Trim()}' → {RowCount} rows";
    }

    [RelayCommand]
    private void ApplyBoardColumnFilters()
    {
        BoardColumnFilterStore.SaveForLane(BoardFilters, DeskLane(), BoardTab == "watchlist");
        ReloadBoard();
        StatusText = $"Column filters → {RowCount} rows";
    }

    private string _progressWinLaneMode = "";

    [RelayCommand]
    private Task OpenScanProgress() =>
        OpenScanProgressFor(SelectedNavId == "backtest" ? "backtest" : "");

    private Task OpenScanProgressFor(string fixedLane)
    {
        try
        {
            Func<string> laneProvider = string.IsNullOrWhiteSpace(fixedLane)
                ? DeskLane
                : () => fixedLane;
            var modeKey = string.IsNullOrWhiteSpace(fixedLane) ? "desk" : fixedLane;
            ShowScanProgress = true;
            StatusText = $"Scan progress · {laneProvider()}";
            if (_progressWin is { IsVisible: true })
            {
                if (_progressWinLaneMode == modeKey)
                {
                    _progressWin.RefreshFromSurface();
                    _progressWin.Activate();
                    return Task.CompletedTask;
                }
                _progressWin.Close();
                _progressWin = null;
            }

            _progressWinLaneMode = modeKey;
            var dlg = new Views.ScanProgressWindow(_surfaces, laneProvider);
            dlg.Closed += (_, _) =>
            {
                if (ReferenceEquals(_progressWin, dlg))
                    _progressWin = null;
            };
            _progressWin = dlg;
            if (Avalonia.Application.Current?.ApplicationLifetime
                is Avalonia.Controls.ApplicationLifetimes.IClassicDesktopStyleApplicationLifetime desk
                && desk.MainWindow is not null)
            {
                dlg.WindowStartupLocation = Avalonia.Controls.WindowStartupLocation.CenterOwner;
                dlg.Show(desk.MainWindow);
            }
            else
                dlg.Show();
        }
        catch (Exception ex)
        {
            StatusText = $"Progress failed: {ex.Message}";
        }
        return Task.CompletedTask;
    }

    private static void SeedScanProgressStarting(string lane, string label)
    {
        try
        {
            var file = lane is "" or "crypto" ? "scan_progress.json" : $"scan_progress_{lane}.json";
            var path = Path.Combine(ProfilePaths.DeviceRoot, file);
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var payload = new System.Text.Json.Nodes.JsonObject
            {
                ["state"] = new System.Text.Json.Nodes.JsonObject
                {
                    ["active"] = true,
                    ["status"] = "running",
                    ["label"] = label,
                    ["phase"] = $"Starting {label}…",
                    ["step_done"] = 0,
                    ["step_total"] = 0,
                    ["pairs_done"] = 0,
                    ["pairs_total"] = 0,
                },
                ["message"] = $"Starting {label}…",
                ["last_seq"] = 0,
                ["events"] = new System.Text.Json.Nodes.JsonArray
                {
                    new System.Text.Json.Nodes.JsonObject
                    {
                        ["seq"] = 1,
                        ["message"] = $"Starting {label}…",
                    }
                },
            };
            File.WriteAllText(path, Services.JsonNodeWrite.ToIndented(payload));
        }
        catch { /* best-effort UI seed */ }
    }

    [RelayCommand]
    private void CreateBotFromSelection()
    {
        var pair = SelectedBoardRow?.Pair ?? FirstBoardPair();
        if (string.IsNullOrWhiteSpace(pair))
        {
            StatusText = "Select a pair first";
            return;
        }
        try
        {
            using var sheet = _surfaces.Fetch("results", DeskLane(), pair);
            var indicator = "RSI";
            if (sheet.RootElement.TryGetProperty("rows", out var rows)
                && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    var ind = S(r, "indicator");
                    if (!string.IsNullOrWhiteSpace(ind)
                        && ind is not "B&H" and not "Oracle max")
                    {
                        indicator = ind;
                        break;
                    }
                }
            }
            using var created = _surfaces.CreateBot(pair, indicator);
            var botName = S(created.RootElement, "name");
            BotsPrefillNote = $"Prefill from scanner · {botName} ({pair} · {indicator})";
            StatusText = BotsPrefillNote;
            Navigate("bots");
        }
        catch (Exception ex)
        {
            StatusText = $"Create Bot failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void OpenBoardGlossary()
    {
        var pair = SelectedBoardRow?.Pair ?? FirstBoardPair();
        GlossaryQuery = string.IsNullOrWhiteSpace(pair) ? "" : pair.Split('/')[0];
        Navigate("glossary");
    }

    private void RefreshDeskLogs()
    {
        BoardRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("alerts", DeskLane(), "logs");
            if (doc.RootElement.TryGetProperty("rows", out var rows)
                && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    BoardRows.Add(new OpportunityBoardRow
                    {
                        Pair = S(r, "pair", "symbol"),
                        Exchange = S(r, "kind"),
                        Health = S(r, "reason"),
                        Gain = 0,
                        VolumeScore = 0,
                    });
                }
            }
            RowCount = BoardRows.Count;
            StatusText = $"Logs: {RowCount} alert rows";
        }
        catch (Exception ex)
        {
            StatusText = $"Logs failed: {ex.Message}";
        }
    }

    private static string S(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (row.TryGetProperty(k, out var p) && p.ValueKind != JsonValueKind.Null)
                return p.ToString();
        }
        return "";
    }

    private static string FirstNonEmpty(string a, string b) =>
        string.IsNullOrWhiteSpace(a) ? b : a;

    private static string? NullIfEmpty(string value) =>
        string.IsNullOrWhiteSpace(value) ? null : value;

    private static double D(JsonElement row, string key) =>
        row.TryGetProperty(key, out var p) && p.TryGetDouble(out var v) ? v : 0;

    private static double? OptD(JsonElement row, string key) =>
        row.TryGetProperty(key, out var p) && p.TryGetDouble(out var v) ? v : null;
}
