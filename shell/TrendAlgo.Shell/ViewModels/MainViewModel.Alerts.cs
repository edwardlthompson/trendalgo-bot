using System.Text.Json;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    private string _alertsToastFingerprint = "";
    [ObservableProperty] private string _telegramVaultStatus = "Telegram credentials: checking…";
    [ObservableProperty] private string _notifyTestResult = "";
    [ObservableProperty] private string _telegramTokenInput = "";
    [ObservableProperty] private string _telegramChatIdInput = "";
    [ObservableProperty] private bool _showTelegramToken;
    [ObservableProperty] private bool _notifyTelegramEnabled = true;

    public char TelegramTokenPasswordChar => ShowTelegramToken ? '\0' : '*';

    partial void OnShowTelegramTokenChanged(bool value) =>
        OnPropertyChanged(nameof(TelegramTokenPasswordChar));

    [RelayCommand]
    private void SelectAlertTab(string? tab)
    {
        if (string.IsNullOrWhiteSpace(tab))
            return;
        AlertTab = tab.Trim().ToLowerInvariant();
        AlertsReload();
    }

    [RelayCommand]
    private void AlertsReload()
    {
        AlertRows.Clear();
        try
        {
            using var doc = _surfaces.Fetch("alerts", "crypto", AlertTab);
            if (doc.RootElement.TryGetProperty("rows", out var rows)
                && rows.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in rows.EnumerateArray())
                {
                    AlertRows.Add(new AlertRow
                    {
                        Kind = Prop(r, "kind"),
                        Pair = Prop(r, "pair", "symbol"),
                        Reason = Prop(r, "reason"),
                        At = LocalTimeFormat.FormatTimestamp(Prop(r, "at")),
                    });
                }
            }
            var total = doc.RootElement.TryGetProperty("total", out var t) ? t.ToString() : "?";
            StatusText = $"Alerts / {AlertTab}: {AlertRows.Count} rows (history {total})";
            if (AlertRows.Count > 0)
                StatusText += $" · latest: {AlertRows[0].Reason}";
            AlertsMaybeToastLatest();
            AlertsRefreshNotifyRibbon();
        }
        catch (Exception ex)
        {
            StatusText = $"Alerts reload failed: {ex.Message}";
        }
    }

    private void AlertsMaybeToastLatest()
    {
        if (AlertRows.Count == 0)
            return;
        var latest = AlertRows[0];
        var fp = $"{latest.At}|{latest.Kind}|{latest.Pair}|{latest.Reason}";
        if (fp == _alertsToastFingerprint)
            return;
        var first = string.IsNullOrEmpty(_alertsToastFingerprint);
        _alertsToastFingerprint = fp;
        if (first)
            return; // seed without toasting history on first load
        var kind = MapAlertToastKind(latest.Kind, AlertTab);
        var title = string.IsNullOrWhiteSpace(latest.Pair) ? "TrendAlgo alert" : latest.Pair;
        var body = string.IsNullOrWhiteSpace(latest.Reason) ? latest.Kind : latest.Reason;
        Toast(title, body, kind);
    }

    private static string MapAlertToastKind(string eventKind, string tab)
    {
        var k = (eventKind ?? "").ToLowerInvariant();
        if (k.Contains("enter") || k.Contains("qualified"))
            return "entered";
        if (k.Contains("leave") || k.Contains("watch"))
            return "left";
        if (k.Contains("trade"))
            return "trades";
        return tab switch
        {
            "entered" => "entered",
            "left" => "left",
            "trades" => "trades",
            _ => "logs",
        };
    }

    private void AlertsRefreshNotifyRibbon()
    {
        try
        {
            using var doc = _surfaces.Fetch("notify", DeskLane());
            if (doc.RootElement.TryGetProperty("ribbon", out var ribbon)
                && ribbon.ValueKind == JsonValueKind.Array)
            {
                var parts = new List<string>();
                foreach (var r in ribbon.EnumerateArray())
                {
                    var label = Prop(r, "label");
                    var state = Prop(r, "state");
                    parts.Add($"{label}·{state}");
                }
                NotifyRibbonText = parts.Count > 0
                    ? "Notify: " + string.Join(" · ", parts)
                    : "Notify: Windows toasts + Telegram stay on device path";
                if (doc.RootElement.TryGetProperty("ribbon_help", out var help))
                    NotifyHelp = help.ToString();
            }
        }
        catch
        {
            /* keep prior ribbon caption */
        }
    }

    [RelayCommand]
    private void AlertsSaveNotify()
    {
        try
        {
            PersistNotifyPrefs();
            AlertsRefreshNotifyRibbon();
            StatusText = "Alerts notify matrix saved (Windows × Telegram)";
        }
        catch (Exception ex)
        {
            StatusText = $"Alerts notify save failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private void AlertsToggleKindMaster(string? kind)
    {
        if (string.IsNullOrWhiteSpace(kind))
            return;
        var id = kind.Trim().ToLowerInvariant();
        var row = NotifyKinds.FirstOrDefault(k =>
            string.Equals(k.Id, id, StringComparison.OrdinalIgnoreCase));
        if (row is null)
        {
            NotifyReload();
            row = NotifyKinds.FirstOrDefault(k =>
                string.Equals(k.Id, id, StringComparison.OrdinalIgnoreCase));
        }
        if (row is null)
            return;
        var next = !(row.Windows && row.Telegram);
        row.Windows = next;
        row.Telegram = next;
        PersistNotifyPrefs();
        AlertsRefreshNotifyRibbon();
        StatusText = $"Alerts · {id} master → {(next ? "On" : "Off")}";
    }

    [RelayCommand]
    private void AlertsTestWindows()
    {
        try
        {
            using var doc = _surfaces.Fetch("notify", DeskLane());
            var kind = AlertTab is "entered" or "left" or "trades" ? AlertTab : "entered";
            string title = "TrendAlgo alert";
            string body = $"Test Windows toast · {kind}";
            if (doc.RootElement.TryGetProperty("ribbon", out var ribbon)
                && ribbon.ValueKind == JsonValueKind.Array)
            {
                foreach (var r in ribbon.EnumerateArray())
                {
                    if (!string.Equals(Prop(r, "id"), kind, StringComparison.OrdinalIgnoreCase))
                        continue;
                    title = Prop(r, "windows_title");
                    body = Prop(r, "windows_body");
                    break;
                }
            }
            Toast(title, body, kind);
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Windows toast preview sent ({kind}).";
            StatusText = $"Windows toast preview · {kind}";
        }
        catch (Exception ex)
        {
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Windows toast test failed: {ex.Message}";
            StatusText = $"Windows toast test failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task SaveTelegramCreds()
    {
        var tok = (TelegramTokenInput ?? "").Trim();
        var chat = (TelegramChatIdInput ?? "").Trim();
        if (string.IsNullOrWhiteSpace(tok) || string.IsNullOrWhiteSpace(chat))
        {
            NotifyTestResult = "Enter both Bot Token and Chat ID before saving.";
            StatusText = NotifyTestResult;
            return;
        }
        try
        {
            _credMan.Write(CredManTargets.TelegramToken, tok);
            _credMan.Write(CredManTargets.TelegramChat, chat);
            NotifyTelegramEnabled = true;
            PersistNotifyPrefs();
            var id = await TelegramDirectClient.GetBotIdentityAsync(tok);
            TelegramVaultStatus = id.Ok
                ? $"Connected: @{id.Username} · Chat ID {TelegramDirectClient.MaskChat(chat)} ✓"
                : $"Saved to Windows CredMan · Chat ID {TelegramDirectClient.MaskChat(chat)} (verify failed: {id.Error})";
            NotifyTestResult = id.Ok
                ? $"[{DateTime.Now:HH:mm:ss}] Saved to Windows CredMan · @{id.Username} ready ✓"
                : $"[{DateTime.Now:HH:mm:ss}] Saved to Windows CredMan, but Telegram check returned: {id.Error}";
            StatusText = TelegramVaultStatus;
        }
        catch (Exception ex)
        {
            NotifyTestResult = $"Save failed: {ex.Message}";
            StatusText = NotifyTestResult;
        }
    }

    [RelayCommand]
    private async Task DetectTelegramChat()
    {
        var tok = (TelegramTokenInput ?? "").Trim();
        if (string.IsNullOrWhiteSpace(tok))
        {
            NotifyTestResult = "Enter your Bot Token first, send /start to the bot in Telegram, then click Detect Chat ID.";
            return;
        }
        NotifyTestResult = "Checking Telegram updates for your Chat ID…";
        var (chatId, err) = await TelegramDirectClient.DetectChatIdAsync(tok);
        if (!string.IsNullOrWhiteSpace(chatId))
        {
            TelegramChatIdInput = chatId;
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Detected Chat ID {TelegramDirectClient.MaskChat(chatId)} — click Save or Test Telegram.";
        }
        else
        {
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Detect failed: {err}";
        }
        StatusText = NotifyTestResult;
    }

    [RelayCommand]
    private async Task AlertsTestTelegram()
    {
        NotifyTestResult = "Sending Telegram test message…";
        StatusText = "Sending Telegram test message…";
        try
        {
            var tok = (TelegramTokenInput ?? "").Trim();
            var chat = (TelegramChatIdInput ?? "").Trim();
            if (string.IsNullOrWhiteSpace(tok))
                tok = (_credMan.Read(CredManTargets.TelegramToken) ?? "").Trim();
            if (string.IsNullOrWhiteSpace(chat))
                chat = (_credMan.Read(CredManTargets.TelegramChat) ?? "").Trim();

            if (string.IsNullOrWhiteSpace(tok) || string.IsNullOrWhiteSpace(chat))
            {
                NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Telegram credentials missing — enter Bot Token & Chat ID above.";
                StatusText = NotifyTestResult;
                return;
            }

            _credMan.Write(CredManTargets.TelegramToken, tok);
            _credMan.Write(CredManTargets.TelegramChat, chat);
            NotifyTelegramEnabled = true;
            PersistNotifyPrefs();

            var res = await TelegramDirectClient.SendMessageAsync(
                tok,
                chat,
                "<b>TrendAlgo</b> — Telegram test notification from Avalonia Shell ✓");
            var id = res.Ok ? await TelegramDirectClient.GetBotIdentityAsync(tok) : null;
            var botLabel = id is { Ok: true } ? $"@{id.Username}" : "bot";
            var masked = TelegramDirectClient.MaskChat(chat);
            if (res.Ok)
            {
                TelegramVaultStatus = $"Connected: {botLabel} · Chat ID {masked} ✓";
                NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] ✓ Test message sent to {botLabel} (chat {masked}).";
                StatusText = $"Telegram test sent ✓ ({botLabel})";
            }
            else
            {
                NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Telegram send failed: {res.Error}";
                StatusText = $"Telegram test failed: {res.Error}";
            }
        }
        catch (Exception ex)
        {
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Telegram test failed: {ex.Message}";
            StatusText = $"Telegram test failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task AlertsTestTelegramRich()
    {
        NotifyTestResult = "Rendering & sending rich Telegram enter alert…";
        StatusText = NotifyTestResult;
        try
        {
            var (ok, photo, pair, err) = await Task.Run(() =>
            {
                using var doc = _surfaces.TestTelegramRich();
                var r = doc.RootElement;
                var passed = r.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
                var hasPhoto = r.TryGetProperty("photo", out var ph) && ph.ValueKind == JsonValueKind.True;
                var sym = r.TryGetProperty("pair", out var pr) ? pr.ToString() : "";
                var error = r.TryGetProperty("error", out var e) && e.ValueKind != JsonValueKind.Null
                    ? e.ToString()
                    : "";
                return (passed, hasPhoto, sym, error);
            });
            NotifyTestResult = ok
                ? $"[{DateTime.Now:HH:mm:ss}] ✓ Rich {(photo ? "chart+table photo" : "HTML")} alert sent for {pair}."
                : $"[{DateTime.Now:HH:mm:ss}] Rich Telegram preview failed: {err}";
            StatusText = NotifyTestResult;
        }
        catch (Exception ex)
        {
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Rich Telegram preview failed: {ex.Message}";
            StatusText = NotifyTestResult;
        }
    }

    [RelayCommand]
    private async Task AlertsTestGrokbot()
    {
        NotifyTestResult = "Sending Grokbot test…";
        StatusText = "Sending Grokbot test…";
        try
        {
            var (ok, err) = await Task.Run(() =>
            {
                using var doc = _surfaces.TestGrokbot();
                var passed = doc.RootElement.TryGetProperty("ok", out var o)
                    && o.ValueKind == JsonValueKind.True;
                var error = doc.RootElement.TryGetProperty("error", out var e)
                    ? e.ToString()
                    : "";
                return (passed, error);
            });
            NotifyTestResult = ok
                ? $"[{DateTime.Now:HH:mm:ss}] Grokbot test succeeded ✓"
                : $"[{DateTime.Now:HH:mm:ss}] Grokbot test failed: {err}";
            StatusText = ok ? "Grokbot test ok" : $"Grokbot test failed: {err}";
        }
        catch (Exception ex)
        {
            NotifyTestResult = $"[{DateTime.Now:HH:mm:ss}] Grokbot test failed: {ex.Message}";
            StatusText = $"Grokbot test failed: {ex.Message}";
        }
    }

    private static string Prop(JsonElement row, params string[] keys)
    {
        foreach (var k in keys)
        {
            if (row.TryGetProperty(k, out var p))
                return p.ToString();
        }
        return "";
    }
}
