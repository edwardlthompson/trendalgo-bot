using System.Text.Json;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private const double DashCell = 36;

    [RelayCommand]
    private void DashboardReload()
    {
        DashboardModules.Clear();
        try
        {
            using var doc = _surfaces.Fetch("dashboard", "crypto");
            var root = doc.RootElement;
            DashboardDemo = root.TryGetProperty("demo", out var d) && d.ValueKind == JsonValueKind.True;
            var cols = 24;
            var gap = 8.0;
            if (root.TryGetProperty("grid", out var grid) && grid.ValueKind == JsonValueKind.Object)
            {
                if (grid.TryGetProperty("cols", out var c) && c.TryGetInt32(out var cv))
                    cols = Math.Max(4, cv);
                if (grid.TryGetProperty("gap_px", out var g) && g.TryGetDouble(out var gv))
                    gap = gv;
            }
            if (root.TryGetProperty("pages", out var pages)
                && pages.ValueKind == JsonValueKind.Array
                && pages.GetArrayLength() > 0)
            {
                var first = pages[0];
                if (root.TryGetProperty("active_page_id", out var ap))
                {
                    var want = ap.ToString();
                    foreach (var p in pages.EnumerateArray())
                    {
                        if (p.TryGetProperty("id", out var id) && id.ToString() == want)
                        {
                            first = p;
                            break;
                        }
                    }
                }
                DashboardPageTitle = first.TryGetProperty("title", out var t) ? t.ToString() : "Main";
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
                    h = Math.Max(1, h);
                    DashboardModules.Add(new DashboardModuleRow
                    {
                        Id = m.TryGetProperty("id", out var id) ? id.ToString() : "",
                        Title = m.TryGetProperty("title", out var title) ? title.ToString() : "",
                        Category = m.TryGetProperty("category", out var cat) ? cat.ToString() : "",
                        Span = $"{w}×{h}",
                        Value = m.TryGetProperty("value", out var val) ? val.ToString() : "",
                        Detail = m.TryGetProperty("detail", out var det) ? det.ToString() : "",
                        PixelLeft = col * DashCell + gap / 2,
                        PixelTop = row * DashCell + gap / 2,
                        PixelWidth = Math.Max(48, w * DashCell - gap),
                        PixelHeight = Math.Max(40, h * DashCell - gap),
                    });
                    i++;
                }
            }
            DashboardCanvasHeight = Math.Max(320, DashboardModules.Select(m => m.PixelTop + m.PixelHeight).DefaultIfEmpty(320).Max() + 24);
            DashboardCanvasWidth = Math.Max(640, cols * DashCell + 24);
            var badge = DashboardDemo ? " · Demo" : "";
            var live = DashboardModules.Count(m => !string.IsNullOrWhiteSpace(m.Value));
            StatusText =
                $"Dashboard · page={DashboardPageTitle} · range={DashboardRange}{badge} · {DashboardModules.Count} tiles · {live} live";
        }
        catch (Exception ex)
        {
            StatusText = $"Dashboard reload failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void DashboardSync()
    {
        DashboardReload();
        PersistDashboardLayout();
        StatusText = $"Sync All · reloaded {DashboardModules.Count} tiles · range={DashboardRange}";
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
    private void SelectDashboardRange(string? range)
    {
        if (string.IsNullOrWhiteSpace(range))
            return;
        DashboardRange = range.Trim().ToUpperInvariant();
        PersistDashboardLayout();
        StatusText = $"Dashboard range → {DashboardRange}";
    }

    [RelayCommand]
    private void DashboardAddPage()
    {
        DashboardPageTitle = "Page " + (DashboardModules.Count % 9 + 2);
        PersistDashboardLayout();
        StatusText = $"Added dashboard page '{DashboardPageTitle}'";
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
    private void DashboardExport()
    {
        var dir = Path.Combine(ProfilePaths.DeviceRoot, "exports");
        Directory.CreateDirectory(dir);
        var stamp = DateTime.Now.ToString("yyyyMMddHHmmss");
        var tsv = Path.Combine(dir, $"dashboard-modules-{stamp}.tsv");
        File.WriteAllLines(tsv, DashboardModules.Select(m => $"{m.Category}\t{m.Id}\t{m.Title}\t{m.Span}\t{m.Value}"));
        var csv = Path.Combine(dir, $"dashboard-holdings-{stamp}.csv");
        File.WriteAllLines(csv,
        [
            "module_id,title,category,span,value,range,page",
            ..DashboardModules.Select(m =>
                $"{m.Id},{Escape(m.Title)},{m.Category},{m.Span},{Escape(m.Value)},{DashboardRange},{DashboardPageTitle}"),
        ]);
        StatusText = $"Exported modules TSV + holdings CSV → {dir}";
    }

    private static string Escape(string s) =>
        s.Contains(',') || s.Contains('"') ? $"\"{s.Replace("\"", "\"\"")}\"" : s;

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
