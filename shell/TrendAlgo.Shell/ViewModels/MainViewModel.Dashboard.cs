using System.Collections.ObjectModel;
using System.Text.Json;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private const double DashCell = 42;

    public ObservableCollection<DashboardPageTab> DashboardPages { get; } = new();

    [ObservableProperty] private bool _isPortfolioSyncing;
    [ObservableProperty] private bool _showDashboardEmptyBanner;
    [ObservableProperty] private string _dashboardMetaSummary = "";

    public string SyncButtonLabel => IsPortfolioSyncing ? "Syncing…" : "Sync Live";
    public string DemoToggleLabel => DashboardDemo ? "Switch to Live" : "Preview Demo";

    partial void OnIsPortfolioSyncingChanged(bool value) => OnPropertyChanged(nameof(SyncButtonLabel));
    partial void OnDashboardDemoChanged(bool value) => OnPropertyChanged(nameof(DemoToggleLabel));

    [RelayCommand]
    private void DashboardReload()
    {
        DashboardModules.Clear();
        DashboardPages.Clear();
        try
        {
            using var doc = _surfaces.Fetch("dashboard", "crypto");
            var root = doc.RootElement;
            DashboardDemo = root.TryGetProperty("demo", out var d) && d.ValueKind == JsonValueKind.True;
            var hasData = root.TryGetProperty("has_data", out var hd) && hd.ValueKind == JsonValueKind.True;
            ShowDashboardEmptyBanner = !hasData && !DashboardDemo;

            if (root.TryGetProperty("active_range", out var ar) && !string.IsNullOrWhiteSpace(ar.ToString()))
                DashboardRange = ar.ToString();

            var cols = 24;
            var gap = 10.0;
            if (root.TryGetProperty("grid", out var grid) && grid.ValueKind == JsonValueKind.Object)
            {
                if (grid.TryGetProperty("cols", out var c) && c.TryGetInt32(out var cv))
                    cols = Math.Max(4, cv);
                if (grid.TryGetProperty("gap_px", out var g) && g.TryGetDouble(out var gv))
                    gap = gv;
            }
            var activePageId = root.TryGetProperty("active_page_id", out var ap) ? ap.ToString() : "";
            if (root.TryGetProperty("pages", out var pages)
                && pages.ValueKind == JsonValueKind.Array
                && pages.GetArrayLength() > 0)
            {
                var first = pages[0];
                foreach (var p in pages.EnumerateArray())
                {
                    var pid = p.TryGetProperty("id", out var id) ? id.ToString() : "";
                    var ptitle = p.TryGetProperty("title", out var pt) ? pt.ToString() : pid;
                    var isActive = string.Equals(pid, activePageId, StringComparison.OrdinalIgnoreCase);
                    if (isActive)
                        first = p;
                    DashboardPages.Add(new DashboardPageTab
                    {
                        Id = pid,
                        Title = ptitle,
                        IsActive = isActive || (string.IsNullOrEmpty(activePageId) && DashboardPages.Count == 0),
                    });
                }
                DashboardPageTitle = first.TryGetProperty("title", out var t) ? t.ToString() : "Overview";
            }

            var tileSource = root.TryGetProperty("tiles", out var tiles) && tiles.ValueKind == JsonValueKind.Array
                ? tiles
                : root.TryGetProperty("modules", out var mods) ? mods : default;
            if (tileSource.ValueKind == JsonValueKind.Array)
            {
                var i = 0;
                foreach (var m in tileSource.EnumerateArray())
                {
                    var col = m.TryGetProperty("col", out var cc) && cc.TryGetInt32(out var cvi) ? cvi : (i % 4) * 6;
                    var row = m.TryGetProperty("row", out var rr) && rr.TryGetInt32(out var rvi) ? rvi : (i / 4) * 4;
                    var w = m.TryGetProperty("w", out var ww) && ww.TryGetInt32(out var wvi) ? wvi : 6;
                    var h = m.TryGetProperty("h", out var hh) && hh.TryGetInt32(out var hvi) ? hvi : 3;
                    w = Math.Clamp(w, 1, cols);
                    h = Math.Max(2, h);
                    DashboardModules.Add(ParseDashboardTile(m, col, row, w, h, gap));
                    i++;
                }
            }
            DashboardCanvasHeight = Math.Max(420, DashboardModules.Select(m => m.PixelTop + m.PixelHeight).DefaultIfEmpty(420).Max() + 28);
            DashboardCanvasWidth = Math.Max(920, cols * DashCell + 24);

            var syncedAt = root.TryGetProperty("last_synced_local", out var ls) ? ls.ToString() : "";
            var venues = root.TryGetProperty("venues_summary", out var vs) ? vs.ToString() : "";
            var badge = DashboardDemo ? "Demo Preview" : "Live";
            DashboardMetaSummary = string.IsNullOrWhiteSpace(syncedAt)
                ? $"{badge} · {venues}"
                : $"{badge} · {venues} · Synced {syncedAt}";
            StatusText = $"Dashboard · {DashboardPageTitle} · {DashboardRange} · {DashboardMetaSummary}";
        }
        catch (Exception ex)
        {
            StatusText = $"Dashboard reload failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task DashboardSync()
    {
        if (IsPortfolioSyncing)
            return;
        IsPortfolioSyncing = true;
        StatusText = "Syncing live balances from CredMan-keyed exchanges…";
        try
        {
            using var doc = await _surfaces.SyncPortfolioAsync();
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            var msg = root.TryGetProperty("message", out var m) ? m.ToString() : "";
            await Dispatcher.UIThread.InvokeAsync(() =>
            {
                DashboardReload();
                PersistDashboardLayout();
                StatusText = ok ? msg : (string.IsNullOrWhiteSpace(msg) ? "Sync skipped — no exchange keys configured" : msg);
            });
        }
        catch (Exception ex)
        {
            StatusText = $"Live sync failed: {ex.Message}";
        }
        finally
        {
            IsPortfolioSyncing = false;
        }
    }

    [RelayCommand]
    private async Task SelectDashboardPage(string? pageId)
    {
        if (string.IsNullOrWhiteSpace(pageId))
            return;
        await ApplyDashboardLayoutAsync($"{{\"active_page_id\":\"{EscapeJson(pageId)}\"}}");
        DashboardReload();
    }

    [RelayCommand]
    private async Task DashboardToggleDemo()
    {
        var nextDemo = !DashboardDemo;
        await ApplyDashboardLayoutAsync($"{{\"demo\":{(nextDemo ? "true" : "false")}}}");
        DashboardReload();
    }

    [RelayCommand]
    private async Task DashboardCustomize()
    {
        try
        {
            using var doc = _surfaces.Fetch("dashboard", DeskLane());
            var dlg = new DashboardCustomizeWindow();
            dlg.Bind(doc.RootElement);
            if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
                {
                    MainWindow: { } owner
                })
                await dlg.ShowDialog(owner);
            else
                dlg.Show();
            if (!dlg.Saved)
                return;
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_dashboard_customize.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var ids = string.Join(",", dlg.SelectedIds.Select(id => $"\"{EscapeJson(id)}\""));
            var json =
                $"{{\"module_ids\":[{ids}],\"cols\":{dlg.Cols},\"rows\":{dlg.Rows},\"show_grid\":{(dlg.ShowGrid ? "true" : "false")}}}";
            File.WriteAllText(path, json);
            using var applied = _surfaces.ApplyDashboardCustomize(path);
            PersistDashboardLayout();
            DashboardReload();
            var count = applied.RootElement.TryGetProperty("count", out var c) ? c.ToString() : "?";
            StatusText = $"Customize applied · {count} modules on '{DashboardPageTitle}'";
        }
        catch (Exception ex)
        {
            StatusText = $"Customize failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task SelectDashboardRange(string? range)
    {
        if (string.IsNullOrWhiteSpace(range))
            return;
        DashboardRange = range.Trim().ToUpperInvariant();
        await ApplyDashboardLayoutAsync($"{{\"range\":\"{EscapeJson(DashboardRange)}\"}}");
        DashboardReload();
    }

    [RelayCommand]
    private async Task DashboardAddPage()
    {
        await ApplyDashboardLayoutAsync("{\"add_page\":true}");
        DashboardReload();
    }

    private async Task ApplyDashboardLayoutAsync(string json)
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_dashboard_layout_apply.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, json);
            using var _ = await _surfaces.ApplyDashboardLayoutAsync(path);
        }
        catch
        {
            /* non-fatal */
        }
    }

    private void PersistDashboardLayout()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_dashboard_layout.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var json =
                $"{{\"page\":\"{EscapeJson(DashboardPageTitle)}\",\"range\":\"{EscapeJson(DashboardRange)}\",\"demo\":{(DashboardDemo ? "true" : "false")}}}";
            File.WriteAllText(path, json);
        }
        catch
        {
            /* non-fatal */
        }
    }

    private static string EscapeJson(string s) =>
        s.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal);

    [RelayCommand]
    private async Task DashboardOpenCalendar()
    {
        await OpenWizard("calendar");
        StatusText = DashboardCalendarCta;
    }

    [RelayCommand]
    private async Task DashboardOpenEvents()
    {
        var pair = string.IsNullOrWhiteSpace(BacktestPair) ? "BTC/USD" : BacktestPair;
        await OpenSurfaceAsync("events", pair);
        StatusText = $"Events timeline · {pair}";
    }

    [RelayCommand]
    private async Task DashboardSharePng()
    {
        try
        {
            var suggested = $"dashboard-{DateTime.Now:yyyy-MM-dd}.png";
            var dest = await SharePngPicker.PickFromMainAsync(suggested);
            if (dest is null)
            {
                StatusText = "Dashboard PNG cancelled";
                return;
            }
            using var doc = _surfaces.SharePng("dashboard", DeskLane(), dest: dest);
            var path = doc.RootElement.TryGetProperty("path", out var p) ? p.ToString() : dest;
            StatusText = string.IsNullOrWhiteSpace(path)
                ? "Dashboard PNG exported"
                : $"Dashboard PNG → {path}";
        }
        catch (Exception ex)
        {
            StatusText = $"Dashboard PNG failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void DashboardExport() => _ = DashboardExportCsv();

    private static DashboardModuleRow ParseDashboardTile(JsonElement m, int col, int row, int w, int h, double gap)
    {
        var series = new List<DashboardChartSeries>();
        if (m.TryGetProperty("series", out var sArr) && sArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var s in sArr.EnumerateArray())
            {
                var pts = new List<DashboardChartPoint>();
                if (s.TryGetProperty("points", out var pArr) && pArr.ValueKind == JsonValueKind.Array)
                {
                    foreach (var pt in pArr.EnumerateArray())
                    {
                        pts.Add(new DashboardChartPoint
                        {
                            X = PropG(pt, "x"),
                            Y = pt.TryGetProperty("y", out var py) && py.TryGetDouble(out var yv) ? yv : 0.0,
                        });
                    }
                }
                series.Add(new DashboardChartSeries
                {
                    Name = PropG(s, "name"),
                    Color = PropG(s, "color"),
                    Points = pts,
                });
            }
        }

        var slices = new List<DashboardSliceItem>();
        if (m.TryGetProperty("slices", out var slArr) && slArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var sl in slArr.EnumerateArray())
            {
                slices.Add(new DashboardSliceItem
                {
                    Label = PropG(sl, "label"),
                    ValueUsd = sl.TryGetProperty("value_usd", out var vu) && vu.TryGetDouble(out var vuv) ? vuv : 0.0,
                    Pct = sl.TryGetProperty("pct", out var pc) && pc.TryGetDouble(out var pcv) ? pcv : 0.0,
                    Color = PropG(sl, "color"),
                });
            }
        }

        var bars = new List<DashboardBarItem>();
        if (m.TryGetProperty("bars", out var bArr) && bArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var b in bArr.EnumerateArray())
            {
                bars.Add(new DashboardBarItem
                {
                    Label = PropG(b, "label"),
                    Value = b.TryGetProperty("value", out var bv) && bv.TryGetDouble(out var bvv) ? bvv : 0.0,
                });
            }
        }

        var cells = new List<DashboardCellItem>();
        if (m.TryGetProperty("cells", out var cArr) && cArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var c in cArr.EnumerateArray())
            {
                cells.Add(new DashboardCellItem
                {
                    Label = PropG(c, "label"),
                    ValueUsd = c.TryGetProperty("value_usd", out var cvu) && cvu.TryGetDouble(out var cvuv) ? cvuv : 0.0,
                    Pct = c.TryGetProperty("pct", out var cpc) && cpc.TryGetDouble(out var cpcv) ? cpcv : 0.0,
                    ChangePct = c.TryGetProperty("change_pct", out var ccp) && ccp.TryGetDouble(out var ccpv) ? ccpv : 0.0,
                });
            }
        }

        var kpis = new List<DashboardKpiItem>();
        if (m.TryGetProperty("kpis", out var kArr) && kArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var k in kArr.EnumerateArray())
            {
                kpis.Add(new DashboardKpiItem
                {
                    Label = PropG(k, "label"),
                    Value = PropG(k, "value"),
                    Sign = k.TryGetProperty("sign", out var ks) && ks.TryGetInt32(out var ksv) ? ksv : 0,
                });
            }
        }

        var ranked = new List<DashboardRankedItem>();
        if (m.TryGetProperty("ranked_rows", out var rArr) && rArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var r in rArr.EnumerateArray())
            {
                ranked.Add(new DashboardRankedItem
                {
                    Label = PropG(r, "label"),
                    Value = PropG(r, "value"),
                    Delta = PropG(r, "delta"),
                    Sign = r.TryGetProperty("sign", out var rs) && rs.TryGetInt32(out var rsv) ? rsv : 0,
                });
            }
        }

        var holdings = new List<DashboardHoldingItem>();
        if (m.TryGetProperty("holdings_rows", out var hArr) && hArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var hr in hArr.EnumerateArray())
            {
                double? chg24 = hr.TryGetProperty("change_24h_pct", out var chgEl) && chgEl.ValueKind == JsonValueKind.Number && chgEl.TryGetDouble(out var chgV)
                    ? chgV
                    : null;
                holdings.Add(new DashboardHoldingItem
                {
                    Asset = PropG(hr, "asset"),
                    Venue = PropG(hr, "venue"),
                    IconPath = PropG(hr, "icon_path"),
                    Quantity = hr.TryGetProperty("quantity", out var qEl) && qEl.TryGetDouble(out var qv) ? qv : 0.0,
                    PriceUsd = hr.TryGetProperty("price_usd", out var pEl) && pEl.TryGetDouble(out var pv) ? pv : 0.0,
                    Change24hPct = chg24,
                    ValueUsd = hr.TryGetProperty("value_usd", out var vEl) && vEl.TryGetDouble(out var vv) ? vv : 0.0,
                    AllocationPct = hr.TryGetProperty("allocation_pct", out var aEl) && aEl.TryGetDouble(out var av) ? av : 0.0,
                    AvgBuyUsd = hr.TryGetProperty("avg_buy_usd", out var abEl) && abEl.TryGetDouble(out var abv) ? abv : 0.0,
                    PnlUsd = hr.TryGetProperty("pnl_usd", out var pnEl) && pnEl.TryGetDouble(out var pnv) ? pnv : 0.0,
                    PnlPct = hr.TryGetProperty("pnl_pct", out var ppEl) && ppEl.TryGetDouble(out var ppv) ? ppv : 0.0,
                });
            }
        }

        var orders = new List<DashboardOrderItem>();
        if (m.TryGetProperty("order_rows", out var oArr) && oArr.ValueKind == JsonValueKind.Array)
        {
            foreach (var ord in oArr.EnumerateArray())
            {
                orders.Add(new DashboardOrderItem
                {
                    Venue = PropG(ord, "venue"),
                    Pair = PropG(ord, "pair"),
                    Side = PropG(ord, "side"),
                    Price = PropG(ord, "price"),
                    Amount = PropG(ord, "amount"),
                });
            }
        }

        return new DashboardModuleRow
        {
            Id = PropG(m, "id"),
            Title = PropG(m, "title"),
            Category = PropG(m, "category"),
            Span = $"{w}×{h}",
            Value = PropG(m, "value"),
            Detail = PropG(m, "detail"),
            VisualKind = string.IsNullOrWhiteSpace(PropG(m, "visual_kind")) ? "kpi_grid" : PropG(m, "visual_kind"),
            DeltaText = PropG(m, "delta_text"),
            DeltaSign = m.TryGetProperty("delta_sign", out var ds) && ds.TryGetInt32(out var dsv) ? dsv : 0,
            GaugeValue = m.TryGetProperty("gauge_value", out var gvEl) && gvEl.TryGetDouble(out var gvv) ? gvv : 0.0,
            GaugeLabel = PropG(m, "gauge_label"),
            PixelLeft = col * DashCell + gap / 2,
            PixelTop = row * DashCell + gap / 2,
            PixelWidth = Math.Max(140, w * DashCell - gap),
            PixelHeight = Math.Max(90, h * DashCell - gap),
            Series = series,
            Slices = slices,
            Bars = bars,
            Cells = cells,
            Kpis = kpis,
            RankedRows = ranked,
            HoldingsRows = holdings,
            OrderRows = orders,
        };
    }

    private void DashboardMinsReload()
    {
        DashboardMinRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("dashboard", DeskLane());
            SettingsEditorBody =
                "Per-module minimum grid sizes for the Dashboard canvas. Overrides persist in portfolio_layout_prefs.json.";
            if (doc.RootElement.TryGetProperty("module_mins", out var mins)
                && mins.ValueKind == JsonValueKind.Array)
            {
                foreach (var m in mins.EnumerateArray())
                {
                    DashboardMinRows.Add(new DashboardMinRow
                    {
                        Id = m.TryGetProperty("id", out var id) ? id.ToString() : "",
                        Title = m.TryGetProperty("title", out var t) ? t.ToString() : "",
                        Category = m.TryGetProperty("category", out var c) ? c.ToString() : "",
                        DefaultW = m.TryGetProperty("default_w", out var dw) && dw.TryGetInt32(out var dwi) ? dwi : 4,
                        DefaultH = m.TryGetProperty("default_h", out var dh) && dh.TryGetInt32(out var dhi) ? dhi : 2,
                        MaxW = m.TryGetProperty("max_w", out var mw) && mw.TryGetInt32(out var mwi) ? mwi : 24,
                        MaxH = m.TryGetProperty("max_h", out var mh) && mh.TryGetInt32(out var mhi) ? mhi : 16,
                        MinW = m.TryGetProperty("min_w", out var w) && w.TryGetInt32(out var wi) ? wi : 4,
                        MinH = m.TryGetProperty("min_h", out var h) && h.TryGetInt32(out var hi) ? hi : 2,
                    });
                }
            }
            StatusText = $"Settings · dashboard · {DashboardMinRows.Count} module mins";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Dashboard mins failed: {ex.Message}";
            StatusText = "Settings · dashboard · error";
        }
    }

    [RelayCommand]
    private void DashboardMinsSave()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_dashboard_mins.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var parts = DashboardMinRows.Select(r =>
                $"{{\"id\":\"{EscapeJson(r.Id)}\",\"min_w\":{r.MinW},\"min_h\":{r.MinH}}}");
            File.WriteAllText(path, $"{{\"mins\":[{string.Join(",", parts)}]}}");
            using var doc = _surfaces.ApplyDashboardMins(path);
            var count = doc.RootElement.TryGetProperty("count", out var c) ? c.ToString() : "?";
            StatusText = $"Dashboard module mins saved · {count} overrides";
            DashboardMinsReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Dashboard mins save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void DashboardMinsReset()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_dashboard_mins.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, "{\"reset\":true}");
            _surfaces.ApplyDashboardMins(path);
            StatusText = "Dashboard module mins reset to catalog defaults";
            DashboardMinsReload();
        }
        catch (Exception ex)
        {
            StatusText = $"Dashboard mins reset failed: {ex.Message}";
        }
    }
}
