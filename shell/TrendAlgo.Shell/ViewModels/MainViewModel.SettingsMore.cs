using System.Text;
using System.Text.Json;
using Avalonia.Controls.ApplicationLifetimes;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void SettingsSave()
    {
        try
        {
            PersistNotifyPrefs();
            if (ShowConnectionEditor)
                ConnectionSave();
            else if (ShowAppearanceEditor)
                AppearanceSave();
            else if (ShowVenueEditor)
                VenueSave();
            else if (ShowLanesEditor)
                LanesSave();
            else if (ShowDashboardMins)
                DashboardMinsSave();
            else if (ShowPrivacyEditor)
                PrivacySave();
            else if (ShowDataEditor)
                DataSave();
            else if (ShowSettingsLayout)
                SettingsLayoutSave();
            else
                SettingsLayoutPersistEditModeOnly();
            StatusText = "Settings saved — ribbon + active section + layout prefs";
        }
        catch (Exception ex)
        {
            StatusText = $"Settings save failed: {ex.Message}";
        }
    }

    private void SettingsLayoutReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("settings_layout", DeskLane());
            var root = doc.RootElement;
            SettingsLayoutEdit = root.TryGetProperty("edit_mode", out var em)
                && em.ValueKind == JsonValueKind.True;
            ShowSettingsLayout = SettingsLayoutEdit;
            SettingsLayoutHelp = root.TryGetProperty("help", out var h) ? h.ToString() : "";
            SettingsNoSecret = root.TryGetProperty("no_secret", out var ns) ? ns.ToString() : "";
            SettingsLayoutRows.Clear();
            var order = new List<string>();
            if (root.TryGetProperty("sections", out var secs) && secs.ValueKind == JsonValueKind.Array)
            {
                foreach (var s in secs.EnumerateArray())
                {
                    var id = s.TryGetProperty("id", out var sid) ? sid.ToString() : "";
                    if (string.IsNullOrEmpty(id))
                        continue;
                    order.Add(id);
                    SettingsLayoutRows.Add(new SettingsLayoutRow
                    {
                        Id = id,
                        Title = s.TryGetProperty("title", out var t) ? t.ToString() : id,
                        MinW = s.TryGetProperty("min_w", out var mw) && mw.TryGetInt32(out var mwi) ? mwi : 8,
                        MinH = s.TryGetProperty("min_h", out var mh) && mh.TryGetInt32(out var mhi) ? mhi : 4,
                        Col = s.TryGetProperty("col", out var c) && c.TryGetInt32(out var ci) ? ci : 0,
                        Row = s.TryGetProperty("row", out var r) && r.TryGetInt32(out var ri) ? ri : 0,
                        W = s.TryGetProperty("w", out var w) && w.TryGetInt32(out var wi) ? wi : 24,
                        H = s.TryGetProperty("h", out var hh) && hh.TryGetInt32(out var hi) ? hi : 8,
                    });
                }
            }
            if (order.Count > 0)
            {
                SettingsSections.Clear();
                foreach (var id in order)
                    SettingsSections.Add(id);
            }
            StatusText = $"Settings · layout · {SettingsLayoutRows.Count} sections";
        }
        catch (Exception ex)
        {
            StatusText = $"Settings layout load failed: {ex.Message}";
        }
    }

    partial void OnSettingsLayoutEditChanged(bool value)
    {
        ShowSettingsLayout = value;
        if (value && SettingsLayoutRows.Count == 0)
            SettingsLayoutReload();
    }

    [RelayCommand]
    private void SettingsLayoutSave()
    {
        try
        {
            WriteSettingsLayoutPayload(reset: false);
            SettingsLayoutReload();
            StatusText = $"Settings layout saved · {SettingsLayoutRows.Count} sections";
        }
        catch (Exception ex)
        {
            StatusText = $"Settings layout save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void SettingsLayoutReset()
    {
        try
        {
            WriteSettingsLayoutPayload(reset: true);
            SettingsLayoutReload();
            StatusText = "Settings layout reset to factory 2-column grid";
        }
        catch (Exception ex)
        {
            StatusText = $"Settings layout reset failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void SettingsLayoutMoveUp()
    {
        if (SelectedSettingsLayoutRow is null)
            return;
        var i = SettingsLayoutRows.IndexOf(SelectedSettingsLayoutRow);
        if (i <= 0)
            return;
        SettingsLayoutRows.Move(i, i - 1);
        RestackSettingsLayoutRows();
    }

    [RelayCommand]
    private void SettingsLayoutMoveDown()
    {
        if (SelectedSettingsLayoutRow is null)
            return;
        var i = SettingsLayoutRows.IndexOf(SelectedSettingsLayoutRow);
        if (i < 0 || i >= SettingsLayoutRows.Count - 1)
            return;
        SettingsLayoutRows.Move(i, i + 1);
        RestackSettingsLayoutRows();
    }

    private void RestackSettingsLayoutRows()
    {
        // Pack into two 24-wide columns like factory_defaults (left then right halves).
        var mid = (SettingsLayoutRows.Count + 1) / 2;
        var leftRow = 0;
        var rightRow = 0;
        for (var i = 0; i < SettingsLayoutRows.Count; i++)
        {
            var row = SettingsLayoutRows[i];
            if (i < mid)
            {
                row.Col = 0;
                row.Row = leftRow;
                row.W = Math.Max(row.MinW, 24);
                leftRow += Math.Max(row.MinH, row.H);
            }
            else
            {
                row.Col = 24;
                row.Row = rightRow;
                row.W = Math.Max(row.MinW, 24);
                rightRow += Math.Max(row.MinH, row.H);
            }
        }
        SettingsSections.Clear();
        foreach (var r in SettingsLayoutRows)
            SettingsSections.Add(r.Id);
    }

    private void SettingsLayoutPersistEditModeOnly()
    {
        try
        {
            WriteSettingsLayoutPayload(reset: false);
        }
        catch
        {
            /* non-fatal on ribbon Save */
        }
    }

    private void WriteSettingsLayoutPayload(bool reset)
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_settings_layout.json");
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        if (reset)
        {
            File.WriteAllText(path,
                $"{{\"reset\":true,\"edit_mode\":{(SettingsLayoutEdit ? "true" : "false")}}}");
        }
        else
        {
            var sb = new StringBuilder();
            sb.Append("{\"edit_mode\":");
            sb.Append(SettingsLayoutEdit ? "true" : "false");
            sb.Append(",\"sections\":[");
            for (var i = 0; i < SettingsLayoutRows.Count; i++)
            {
                if (i > 0)
                    sb.Append(',');
                var r = SettingsLayoutRows[i];
                sb.Append('{');
                sb.Append($"\"id\":\"{EscapeJson(r.Id)}\",");
                sb.Append($"\"col\":{r.Col},\"row\":{r.Row},\"w\":{r.W},\"h\":{r.H}");
                sb.Append('}');
            }
            sb.Append("]}");
            File.WriteAllText(path, sb.ToString());
        }
        using var doc = _surfaces.ApplySettingsLayout(path);
        var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
        if (!ok)
        {
            var err = doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "error";
            throw new InvalidOperationException(err);
        }
    }

    private void PersistNotifyPrefs()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, "notify_prefs.json");
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        bool Kind(string id, bool fallback)
        {
            var row = NotifyKinds.FirstOrDefault(k =>
                string.Equals(k.Id, id, StringComparison.OrdinalIgnoreCase));
            return row?.Telegram ?? fallback;
        }
        bool Win(string id, bool fallback)
        {
            var row = NotifyKinds.FirstOrDefault(k =>
                string.Equals(k.Id, id, StringComparison.OrdinalIgnoreCase));
            return row?.Windows ?? fallback;
        }
        var hasTgCreds = _credMan.Has(CredManTargets.TelegramToken)
            && _credMan.Has(CredManTargets.TelegramChat);
        var tgEnabled = NotifyTelegramEnabled || hasTgCreds;
        var json =
            "{"
            + $"\"telegram_enabled\":{(tgEnabled ? "true" : "false")},"
            + $"\"start_with_windows\":{(NotifyAutostart ? "true" : "false")},"
            + $"\"windows_logs\":{(Win("logs", true) ? "true" : "false")},"
            + $"\"windows_entered\":{(Win("entered", true) ? "true" : "false")},"
            + $"\"windows_left\":{(Win("left", true) ? "true" : "false")},"
            + $"\"windows_trades\":{(Win("trades", true) ? "true" : "false")},"
            + $"\"telegram_logs\":{(Kind("logs", true) ? "true" : "false")},"
            + $"\"telegram_entered\":{(Kind("entered", true) ? "true" : "false")},"
            + $"\"telegram_left\":{(Kind("left", true) ? "true" : "false")},"
            + $"\"telegram_trades\":{(Kind("trades", true) ? "true" : "false")}"
            + "}";
        File.WriteAllText(path, json);
        AutostartRegistry.SetEnabled(NotifyAutostart);
    }

    [RelayCommand]
    private void ToggleNotifyAutostart()
    {
        NotifyAutostart = !NotifyAutostart;
        PersistNotifyPrefs();
        StatusText = NotifyAutostart
            ? "Start with Windows: on (HKCU Run)"
            : "Start with Windows: off";
    }

    [RelayCommand]
    private async Task OpenWizard(string? which)
    {
        var name = string.IsNullOrWhiteSpace(which) ? "setup" : which.Trim().ToLowerInvariant();
        if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
            {
                MainWindow: { } owner
            })
        {
            var dlg = new WizardWindow(name);
            var saved = await dlg.ShowDialog<bool?>(owner);
            if (saved == true && name == "telegram")
                RefreshTelegramVaultStatus();
            else if (saved == true && name == "keys")
                SelectSettingsSection("keys");
            else if (saved == true)
                CredmanReloadSafe();
            StatusText = saved == true
                ? $"{name} wizard saved to CredMan"
                : $"{name} wizard closed";
            return;
        }
        StatusText = $"{name} wizard — no owner window";
    }

    private void CredmanReloadSafe()
    {
        try
        {
            if (SettingsSection == "keys")
                SelectSettingsSection("keys");
        }
        catch
        {
            /* ignore */
        }
    }

    [RelayCommand]
    private async Task OpenFeedback()
    {
        AboutReload();
        string version = "", body = "", donate = "", changelog = "";
        try
        {
            using var doc = _surfaces.Fetch("about", "crypto");
            version = doc.RootElement.TryGetProperty("version_line", out var v) ? v.ToString() : "";
            body = doc.RootElement.TryGetProperty("body", out var b) ? b.ToString() : "";
            donate = doc.RootElement.TryGetProperty("donate", out var d) ? d.ToString() : "";
            changelog = doc.RootElement.TryGetProperty("changelog_url", out var c) ? c.ToString() : "";
        }
        catch
        {
            // dialog still opens with blanks
        }
        if (Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime
            {
                MainWindow: { } owner
            })
        {
            var dlg = new FeedbackWindow(version, body, donate, changelog);
            await dlg.ShowDialog(owner);
            StatusText = "Feedback / update prompt closed";
        }
    }

    [RelayCommand]
    private void MoreSurfaceNote()
    {
        StatusText = SelectedNavId switch
        {
            "glossary" => "Glossary — strategy term popups; content still engine/strings-backed",
            "export" => "Export hub — journal CSV, plan JSON, latest scan JSON",
            "billing" => "Billing — owner-only settle copy; H-006b still HUMAN",
            "debug" => "Debug — device.log + TRENDALGO_DEBUG_SCAN force-fresh",
            "wizards" => "Wizards — Avalonia step UI; CredMan secret entry on device",
            _ => StatusText,
        };
    }

    private void ExportHubReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("export_hub", DeskLane());
            var root = doc.RootElement;
            ExportHubTitle = root.TryGetProperty("title", out var t) ? t.ToString() : "Export";
            ExportHubSubtitle = root.TryGetProperty("subtitle", out var s) ? s.ToString() : "";
            ExportHubFolder = root.TryGetProperty("folder", out var f) ? f.ToString() : "";
            ExportHubFolderHelp = root.TryGetProperty("folder_help", out var h) ? h.ToString() : "";
            ExportJournalLabel = root.TryGetProperty("journal_label", out var j) ? j.ToString() : ExportJournalLabel;
            ExportPlanLabel = root.TryGetProperty("plan_label", out var p) ? p.ToString() : ExportPlanLabel;
            ExportScanLabel = root.TryGetProperty("scan_label", out var sc) ? sc.ToString() : ExportScanLabel;
            ExportHubStatus = root.TryGetProperty("folder_label", out var fl) ? fl.ToString() : "";
            PageBody = ExportHubSubtitle;
            StatusText = "Export hub ready";
        }
        catch (Exception ex)
        {
            ExportHubStatus = $"Export hub load failed: {ex.Message}";
            StatusText = "Export · error";
        }
    }

    [RelayCommand]
    private void ExportHubRun(string? kind)
    {
        var which = string.IsNullOrWhiteSpace(kind) ? "" : kind.Trim().ToLowerInvariant();
        if (which is not ("journal" or "plan" or "scan"))
        {
            StatusText = "Export kind required";
            return;
        }
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_export_hub.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var dest = EscapeJson(ExportHubFolder ?? "");
            File.WriteAllText(path, $"{{\"kind\":\"{which}\",\"dest\":\"{dest}\"}}");
            using var doc = _surfaces.ExportHub(path);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var problems = root.TryGetProperty("problems", out var p)
                    && p.ValueKind == JsonValueKind.Array
                    ? string.Join(" ", p.EnumerateArray().Select(x => x.ToString()))
                    : "export failed";
                ExportHubStatus = problems;
                StatusText = $"Export {which} failed";
                return;
            }
            ExportHubStatus = root.TryGetProperty("message", out var m) ? m.ToString() : "Exported";
            if (root.TryGetProperty("folder", out var folder))
                ExportHubFolder = folder.ToString();
            StatusText = ExportHubStatus;
        }
        catch (Exception ex)
        {
            ExportHubStatus = $"Export failed: {ex.Message}";
            StatusText = $"Export {which} failed";
        }
    }
}
