using System.Text;
using System.Text.Json;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private readonly WindowsCredManStore _credMan = new();

    [RelayCommand]
    private void GlossarySearch()
    {
        GlossaryRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("glossary", "crypto", GlossaryQuery);
            if (doc.RootElement.TryGetProperty("rows", out var rows)
                && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    GlossaryRows.Add(new GlossaryRow
                    {
                        Id = PropG(r, "id"),
                        Title = PropG(r, "title"),
                        Category = PropG(r, "category"),
                        Short = PropG(r, "short"),
                    });
                }
            }
            var shown = doc.RootElement.TryGetProperty("shown", out var s) ? s.ToString() : "?";
            var total = doc.RootElement.TryGetProperty("total", out var t) ? t.ToString() : "?";
            StatusText = $"Glossary {shown}/{total} · query='{GlossaryQuery}'";
        }
        catch (Exception ex)
        {
            StatusText = $"Glossary failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void DebugReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("debug", "crypto");
            var lines = new List<string>();
            if (doc.RootElement.TryGetProperty("lines", out var arr)
                && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var ln in arr.EnumerateArray())
                    lines.Add(ln.ToString());
            }
            DebugLogText = lines.Count == 0
                ? "(no device.log yet)"
                : string.Join('\n', lines.TakeLast(80));
            StatusText = $"Debug log · {lines.Count} lines";
        }
        catch (Exception ex)
        {
            StatusText = $"Debug failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void BillingReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("billing", "crypto");
            BillingTitle = PropG(doc.RootElement, "title");
            if (string.IsNullOrWhiteSpace(BillingTitle))
                BillingTitle = "Billing";
            var sub = PropG(doc.RootElement, "subtitle");
            var body = PropG(doc.RootElement, "owner_body");
            BillingBody = string.IsNullOrWhiteSpace(sub) ? body : sub + "\n\n" + body;
            BillingSettleHelp = PropG(doc.RootElement, "settle_help");
            StatusText = "Billing · owner-only (settle disabled until H-006)";
        }
        catch (Exception ex)
        {
            StatusText = $"Billing failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void AboutReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("about", "crypto");
            var parts = new List<string>
            {
                PropG(doc.RootElement, "version_line"),
                PropG(doc.RootElement, "body"),
                PropG(doc.RootElement, "donate"),
                "Changelog: " + PropG(doc.RootElement, "changelog_url"),
            };
            AboutText = string.Join("\n\n", parts.Where(p => !string.IsNullOrWhiteSpace(p)));
            StatusText = PropG(doc.RootElement, "version_line");
        }
        catch (Exception ex)
        {
            StatusText = $"About failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void NotifyReload()
    {
        NotifyKinds.Clear();
        try
        {
            using var doc = _surfaces.Fetch("notify", "crypto");
            NotifyHelp = PropG(doc.RootElement, "help");
            NotifyGrokHelp = PropG(doc.RootElement, "grokbot_help");
            NotifyAutostart = doc.RootElement.TryGetProperty("start_with_windows", out var a)
                && a.ValueKind == JsonValueKind.True;
            NotifyTelegramEnabled = doc.RootElement.TryGetProperty("telegram_enabled", out var te)
                ? te.ValueKind == JsonValueKind.True
                : (_credMan.Has(CredManTargets.TelegramToken) && _credMan.Has(CredManTargets.TelegramChat));
            if (doc.RootElement.TryGetProperty("kinds", out var kinds)
                && kinds.ValueKind == JsonValueKind.Array)
            {
                foreach (var k in kinds.EnumerateArray())
                {
                    NotifyKinds.Add(new NotifyKindRow
                    {
                        Id = PropG(k, "id"),
                        Label = PropG(k, "label"),
                        Windows = k.TryGetProperty("windows", out var w) && w.ValueKind == JsonValueKind.True,
                        Telegram = k.TryGetProperty("telegram", out var tg) && tg.ValueKind == JsonValueKind.True,
                    });
                }
            }
            StatusText = $"Notify matrix · {NotifyKinds.Count} kinds · autostart={NotifyAutostart}";
            RefreshTelegramVaultStatus();
        }
        catch (Exception ex)
        {
            StatusText = $"Notify reload failed: {ex.Message}";
        }
    }

    private void RefreshTelegramVaultStatus()
    {
        try
        {
            var tok = (_credMan.Read(CredManTargets.TelegramToken) ?? "").Trim();
            var chat = (_credMan.Read(CredManTargets.TelegramChat) ?? "").Trim();
            if (!string.IsNullOrEmpty(tok) && string.IsNullOrEmpty(TelegramTokenInput))
                TelegramTokenInput = tok;
            if (!string.IsNullOrEmpty(chat) && string.IsNullOrEmpty(TelegramChatIdInput))
                TelegramChatIdInput = chat;
            if (!string.IsNullOrEmpty(tok) && !string.IsNullOrEmpty(chat))
            {
                var masked = TelegramDirectClient.MaskChat(chat);
                TelegramVaultStatus = $"Telegram credentials: Loaded from Windows CredMan (chat {masked}) · verifying…";
                _ = VerifyTelegramIdentityAsync(tok, masked);
            }
            else
            {
                TelegramVaultStatus =
                    "Telegram credentials: Missing — paste your Bot Token & Chat ID below, or click Detect Chat ID.";
            }
        }
        catch
        {
            TelegramVaultStatus = "Telegram credentials: Check CredMan in API Keys & Connection.";
        }
    }

    private async Task VerifyTelegramIdentityAsync(string tok, string maskedChat)
    {
        var id = await TelegramDirectClient.GetBotIdentityAsync(tok);
        Avalonia.Threading.Dispatcher.UIThread.Post(() =>
        {
            TelegramVaultStatus = id.Ok
                ? $"Connected: @{id.Username} · Chat ID {maskedChat} ✓"
                : $"CredMan loaded (chat {maskedChat}) · Bot verify: {id.Error}";
        });
    }

    internal static string NormalizeSettingsSection(string? section)
    {
        var sec = (section ?? "notify").Trim().ToLowerInvariant();
        return sec switch
        {
            "venue" => "lanes",
            "connection" => "keys",
            "dashboard" => "appearance",
            "privacy" or "export" => "data",
            "billing" or "glossary" or "debug" or "updates" => "about",
            "alerts" or "notify" => "notify",
            "lanes" or "keys" or "appearance" or "data" or "about" => sec,
            _ => "notify",
        };
    }

    [RelayCommand]
    private void SelectSettingsSection(string? section)
    {
        if (string.IsNullOrWhiteSpace(section))
            return;
        SettingsSection = NormalizeSettingsSection(section);
        ShowNotifyMatrix = SettingsSection == "notify";
        ShowLanesEditor = SettingsSection == "lanes";
        ShowVenueEditor = SettingsSection == "lanes";
        ShowKeysEditor = SettingsSection == "keys";
        ShowConnectionEditor = SettingsSection == "keys";
        ShowAppearanceEditor = SettingsSection == "appearance";
        ShowDashboardMins = SettingsSection == "appearance";
        ShowDataEditor = SettingsSection == "data";
        ShowPrivacyEditor = SettingsSection == "data";
        ShowExportHub = SettingsSection == "data";
        ShowUpdatesEditor = SettingsSection == "about";
        if (ShowNotifyMatrix)
        {
            NotifyReload();
            AlertsReload();
        }
        else if (ShowLanesEditor)
        {
            LanesReload();
            VenueReload();
        }
        else if (ShowKeysEditor)
        {
            CredmanReload();
            ConnectionReload();
        }
        else if (ShowAppearanceEditor)
        {
            AppearanceReload();
            DashboardMinsReload();
        }
        else if (ShowDataEditor)
        {
            DataReload();
            ExportHubReload();
            PrivacyReload();
        }
        else if (ShowUpdatesEditor)
        {
            AboutReload();
            UpdatesReload();
            BillingReload();
            DebugReload();
        }
        else
            SettingsEditorBody = SettingsSection switch
            {
                "notify" => "Windows × Telegram matrix below (read from notify_prefs.json).",
                _ => "Settings section",
            };
        SettingsEditorNote = SettingsSection == "keys"
            ? "Same TrendAlgo/* CredMan targets as Bot — no re-entry. Wizards write these targets in AV-P1h."
            : SettingsSection is "privacy" or "venue"
                ? "Non-secret prefs here; vault secrets use frozen CredMan targets."
                : "Shell editors cover non-secret prefs; secrets stay in CredMan.";
        if (SettingsSection != "keys")
            StatusText = $"Settings · {SettingsSection}";
    }

    private void CredmanReload()
    {
        var sb = new StringBuilder();
        sb.AppendLine("CredMan continuity (presence only — secrets never shown)");
        sb.AppendLine(CredManTargets.AlgoSpecialNote);
        try
        {
            using var doc = _surfaces.Fetch("credman", "crypto");
            var root = doc.RootElement;
            var present = root.TryGetProperty("present", out var p) ? p.GetInt32() : 0;
            var total = root.TryGetProperty("total", out var t) ? t.GetInt32() : 0;
            sb.AppendLine($"Engine inventory: {present}/{total} present");
            if (root.TryGetProperty("rows", out var rows) && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var row in rows.EnumerateArray())
                {
                    var kind = PropG(row, "kind");
                    var target = PropG(row, "target");
                    var on = row.TryGetProperty("present", out var pr) && pr.ValueKind == JsonValueKind.True;
                    var shellHas = !string.IsNullOrEmpty(target) && _credMan.Has(target);
                    var mark = on ? "present" : "missing";
                    var agree = on == shellHas ? "ok" : "mismatch";
                    sb.AppendLine($"  [{mark}] {kind} · shell={agree}");
                }
            }
            StatusText = $"Settings · keys · CredMan {present}/{total}";
        }
        catch (Exception ex)
        {
            sb.AppendLine($"Engine inventory failed: {ex.Message}");
            foreach (var (kind, target, on) in _credMan.CorePresence())
                sb.AppendLine($"  [{(on ? "present" : "missing")}] {kind} (shell-only)");
            StatusText = $"Settings · keys · shell CredMan fallback";
        }
        SettingsEditorBody = sb.ToString().TrimEnd();
    }

    private void ConnectionReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("connection", DeskLane());
            var root = doc.RootElement;
            ConnectionOwnerId = root.TryGetProperty("owner_id", out var o) ? o.ToString() : "";
            ConnectionHostUrl = root.TryGetProperty("host_url", out var h) ? h.ToString() : "";
            ConnectionCertPin = root.TryGetProperty("cert_sha256", out var c) ? c.ToString() : "";
            ConnectionHelp = root.TryGetProperty("help", out var help) ? help.ToString() : "";
            ConnectionFirstRun = root.TryGetProperty("first_run", out var fr)
                && fr.ValueKind == JsonValueKind.True;
            SettingsEditorBody = ConnectionFirstRun
                ? "Connection — first run (Owner ID required to save)"
                : "Connection — owner / host / cert pin";
            StatusText = string.IsNullOrEmpty(ConnectionOwnerId)
                ? "Settings · connection · unset"
                : $"Settings · connection · {ConnectionOwnerId}";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Connection load failed: {ex.Message}";
            StatusText = "Settings · connection · error";
        }
    }

    [RelayCommand]
    private void ConnectionSave()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_connection.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var owner = EscapeJson(ConnectionOwnerId ?? "");
            var host = EscapeJson(ConnectionHostUrl ?? "");
            var pin = EscapeJson(ConnectionCertPin ?? "");
            File.WriteAllText(path,
                $"{{\"owner_id\":\"{owner}\",\"host_url\":\"{host}\",\"cert_sha256\":\"{pin}\"}}");
            using var doc = _surfaces.ApplyConnection(path);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var problems = doc.RootElement.TryGetProperty("problems", out var p)
                    && p.ValueKind == JsonValueKind.Array
                    ? string.Join(" ", p.EnumerateArray().Select(x => x.ToString()))
                    : (doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "error");
                StatusText = $"Connection save failed: {problems}";
                return;
            }
            ConnectionReload();
            RefreshHandshake();
            StatusText = $"Connection saved · {ConnectionOwnerId}";
        }
        catch (Exception ex)
        {
            StatusText = $"Connection save failed: {ex.Message}";
        }
    }

    private void AppearanceReload()
    {
        var (theme, accent) = ShellTheme.LoadFromSettings();
        ThemeMode = theme;
        AccentColor = accent;
        SettingsEditorBody =
            "Appearance — theme and accent write settings.json (same file as PySide). "
            + "Empty accent = Fluent default. Top bar Theme/Accent still cycle the same prefs.";
        StatusText =
            $"Settings · appearance · {ThemeMode} / {(string.IsNullOrEmpty(AccentColor) ? "default" : AccentColor)}";
    }

    private void PrivacyReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("privacy", DeskLane());
            var root = doc.RootElement;
            PrivacySaveCrashes = root.TryGetProperty("save_crashes", out var sc)
                && sc.ValueKind == JsonValueKind.True;
            PrivacyLabel = root.TryGetProperty("label", out var l) ? l.ToString() : "Save crashes";
            PrivacyHelp = root.TryGetProperty("help", out var h) ? h.ToString() : "";
            SettingsEditorBody = root.TryGetProperty("section", out var sec) ? sec.ToString() : "Privacy";
            StatusText = $"Settings · privacy · save_crashes={PrivacySaveCrashes}";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Privacy load failed: {ex.Message}";
            StatusText = "Settings · privacy · error";
        }
    }

    [RelayCommand]
    private void PrivacySave()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_privacy.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path, $"{{\"save_crashes\":{(PrivacySaveCrashes ? "true" : "false")}}}");
            using var doc = _surfaces.ApplyPrivacy(path);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                StatusText = "Privacy save failed";
                return;
            }
            PrivacyReload();
            StatusText = $"Privacy saved · save_crashes={PrivacySaveCrashes}";
        }
        catch (Exception ex)
        {
            StatusText = $"Privacy save failed: {ex.Message}";
        }
    }

    private void DataReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("data", DeskLane());
            var root = doc.RootElement;
            DataHelp = root.TryGetProperty("help", out var h) ? h.ToString() : "";
            DataExportDir = root.TryGetProperty("export_dir", out var ed) ? ed.ToString()
                : (root.TryGetProperty("last_export_dir", out var led) ? led.ToString() : "");
            DataUseUtc = root.TryGetProperty("use_utc", out var u) && u.ValueKind == JsonValueKind.True;
            DataUseUtcLabel = root.TryGetProperty("use_utc_label", out var ul) ? ul.ToString() : "UTC";
            DataUseUtcHelp = root.TryGetProperty("use_utc_help", out var uh) ? uh.ToString() : "";
            DataProfileRoot = root.TryGetProperty("profile_root", out var pr) ? pr.ToString() : "";
            SettingsEditorBody = "Data — exports folder + UTC display";
            StatusText = $"Settings · data · utc={DataUseUtc}";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Data load failed: {ex.Message}";
            StatusText = "Settings · data · error";
        }
    }

    [RelayCommand]
    private void DataSave()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_data.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var dir = EscapeJson(DataExportDir ?? "");
            File.WriteAllText(path,
                $"{{\"last_export_dir\":\"{dir}\",\"use_utc\":{(DataUseUtc ? "true" : "false")}}}");
            using var doc = _surfaces.ApplyData(path);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var problems = doc.RootElement.TryGetProperty("problems", out var p)
                    && p.ValueKind == JsonValueKind.Array
                    ? string.Join(" ", p.EnumerateArray().Select(x => x.ToString()))
                    : "error";
                StatusText = $"Data save failed: {problems}";
                return;
            }
            DataReload();
            StatusText = $"Data saved · utc={DataUseUtc}";
        }
        catch (Exception ex)
        {
            StatusText = $"Data save failed: {ex.Message}";
        }
    }

    private void UpdatesReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("updates", DeskLane());
            var root = doc.RootElement;
            UpdatesVersionLine = root.TryGetProperty("version_line", out var v) ? v.ToString() : "";
            UpdatesSupport = root.TryGetProperty("support", out var s) ? s.ToString() : "";
            UpdatesChangelogUrl = root.TryGetProperty("changelog_url", out var c) ? c.ToString() : "";
            UpdatesLastSeen = root.TryGetProperty("last_seen_version", out var ls) ? ls.ToString() : "";
            UpdatesStatus = string.IsNullOrEmpty(UpdatesLastSeen)
                ? "No update check recorded yet."
                : $"Last seen version: {UpdatesLastSeen}";
            SettingsEditorBody = "About — version / updates / donate";
            StatusText = "Settings · about · updates";
        }
        catch (Exception ex)
        {
            UpdatesStatus = $"Updates load failed: {ex.Message}";
            StatusText = "Settings · about · error";
        }
    }

    [RelayCommand]
    private void UpdatesCheck()
    {
        try
        {
            using var doc = _surfaces.CheckUpdates();
            var root = doc.RootElement;
            UpdatesStatus = root.TryGetProperty("message", out var m) ? m.ToString() : "Checked";
            if (root.TryGetProperty("prefs", out var prefs) && prefs.ValueKind == JsonValueKind.Object)
            {
                UpdatesVersionLine = prefs.TryGetProperty("version_line", out var v) ? v.ToString() : UpdatesVersionLine;
                UpdatesLastSeen = prefs.TryGetProperty("last_seen_version", out var ls) ? ls.ToString() : UpdatesLastSeen;
            }
            StatusText = $"Updates · {UpdatesStatus}";
        }
        catch (Exception ex)
        {
            UpdatesStatus = $"Update check failed: {ex.Message}";
            StatusText = "Settings · about · check failed";
        }
    }

    [RelayCommand]
    private void UpdatesOpenChangelog()
    {
        if (string.IsNullOrWhiteSpace(UpdatesChangelogUrl))
        {
            StatusText = "Changelog URL missing";
            return;
        }
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = UpdatesChangelogUrl,
                UseShellExecute = true,
            });
            StatusText = "Opened changelog";
        }
        catch (Exception ex)
        {
            StatusText = $"Changelog open failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void AppearanceSave()
    {
        try
        {
            var theme = ThemeMode?.Trim().ToLowerInvariant() ?? "system";
            if (!ShellTheme.ThemeChoices.Contains(theme))
                theme = "system";
            var accent = AccentColor ?? "";
            if (!ShellTheme.AccentPresets.Contains(accent, StringComparer.OrdinalIgnoreCase))
                accent = "";
            ThemeMode = theme;
            AccentColor = accent;
            ShellTheme.Persist(theme, accent);
            StatusText =
                $"Appearance saved · {theme} / {(string.IsNullOrEmpty(accent) ? "default" : accent)}";
        }
        catch (Exception ex)
        {
            StatusText = $"Appearance save failed: {ex.Message}";
        }
    }

    private void LanesReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("lanes", DeskLane());
            var root = doc.RootElement;
            LanesHint = root.TryGetProperty("hint", out var h) ? h.ToString() : "";
            LanesAlpacaHint = root.TryGetProperty("alpaca_hint", out var ah) ? ah.ToString() : "";
            LanesAlpacaKeyed = root.TryGetProperty("alpaca_keyed", out var ak)
                && ak.ValueKind == JsonValueKind.True;
            LaneAutoCrypto = root.TryGetProperty("auto_scan_crypto", out var c)
                && c.ValueKind == JsonValueKind.True;
            LaneAutoTradfi = root.TryGetProperty("auto_scan_tradfi", out var t)
                && t.ValueKind == JsonValueKind.True;
            LaneAutoForex = root.TryGetProperty("auto_scan_forex", out var f)
                && f.ValueKind == JsonValueKind.True;
            LanesIntervalMinutes = AutoScanSchedulerService.LoadConfig().IntervalMinutes;
            RefreshAutoScanScheduler();
            SettingsEditorBody = "Market lanes — Auto-scan per desk & hourly schedule";
            StatusText = LanesAlpacaKeyed
                ? "Settings · lanes · Alpaca keyed"
                : "Settings · lanes · Alpaca keys missing for TradFi/Forex";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Lanes load failed: {ex.Message}";
            StatusText = "Settings · lanes · error";
        }
    }

    [RelayCommand]
    private void LanesSave()
    {
        try
        {
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_lanes.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(path,
                "{"
                + $"\"auto_scan_crypto\":{(LaneAutoCrypto ? "true" : "false")},"
                + $"\"auto_scan_tradfi\":{(LaneAutoTradfi ? "true" : "false")},"
                + $"\"auto_scan_forex\":{(LaneAutoForex ? "true" : "false")}"
                + "}");
            using var doc = _surfaces.ApplyLanes(path);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                StatusText = "Lanes save failed";
                return;
            }
            SaveIntervalMinutesToFilters((int)LanesIntervalMinutes);
            RefreshAutoScanScheduler();
            LanesReload();
            StatusText =
                $"Lanes saved · crypto={LaneAutoCrypto} tradfi={LaneAutoTradfi} forex={LaneAutoForex} · every {(int)LanesIntervalMinutes}m";
        }
        catch (Exception ex)
        {
            StatusText = $"Lanes save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task LanesOpenAlpaca() => await OpenWizard("alpaca");

    private void VenueReload()
    {
        try
        {
            using var doc = _surfaces.Fetch("venue", DeskLane());
            var root = doc.RootElement;
            VenueChoice = root.TryGetProperty("venue", out var v) ? v.ToString() : "host";
            VenueAck = root.TryGetProperty("disclosure_accepted", out var a)
                && a.ValueKind == JsonValueKind.True;
            VenueAckLocked = VenueAck;
            VenueDisclosure = root.TryGetProperty("disclosure_text", out var d) ? d.ToString() : "";
            SettingsEditorBody = root.TryGetProperty("label", out var lab)
                ? lab.ToString()
                : "Execution venue";
            StatusText = $"Settings · venue · {VenueChoice}";
        }
        catch (Exception ex)
        {
            SettingsEditorBody = $"Venue load failed: {ex.Message}";
            StatusText = "Settings · venue · error";
        }
    }

    [RelayCommand]
    private void VenueSelectHost()
    {
        VenueChoice = "host";
        StatusText = "Venue → host";
    }

    [RelayCommand]
    private void VenueSelectDevice()
    {
        VenueChoice = "device";
        StatusText = "Venue → device (ack disclosure to save)";
    }

    [RelayCommand]
    private void VenueSave()
    {
        try
        {
            if (VenueChoice == "device" && !VenueAck && !VenueAckLocked)
            {
                StatusText = "Venue save blocked — accept disclosure for device execution";
                return;
            }
            var path = Path.Combine(ProfilePaths.DeviceRoot, "shell_venue.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            var ack = VenueAck || VenueAckLocked;
            var safeVenue = VenueChoice.Replace("\\", "\\\\", StringComparison.Ordinal)
                .Replace("\"", "\\\"", StringComparison.Ordinal);
            File.WriteAllText(path,
                $"{{\"venue\":\"{safeVenue}\",\"disclosure_accepted\":{(ack ? "true" : "false")}}}");
            using var doc = _surfaces.ApplyVenue(path);
            var ok = doc.RootElement.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var err = doc.RootElement.TryGetProperty("error", out var e) ? e.ToString() : "error";
                StatusText = $"Venue save failed: {err}";
                return;
            }
            VenueReload();
            StatusText = $"Venue saved · {VenueChoice}";
        }
        catch (Exception ex)
        {
            StatusText = $"Venue save failed: {ex.Message}";
        }
    }

    private static string PropG(JsonElement row, string key) =>
        row.TryGetProperty(key, out var p) ? p.ToString() : "";
}
