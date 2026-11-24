using System.Net.Http;
using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Direct Telegram Bot API client for instant UI verification, chat detection, and test sends.</summary>
public static class TelegramDirectClient
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(15) };

    public sealed record BotIdentity(bool Ok, string Username, string FirstName, string? Error);
    public sealed record SendResult(bool Ok, string? Error);

    public static string MaskChat(string? chatId)
    {
        var s = (chatId ?? "").Trim();
        if (s.Length <= 4)
            return string.IsNullOrEmpty(s) ? "" : "***";
        return $"{s[..2]}***{s[^2..]}";
    }

    public static async Task<BotIdentity> GetBotIdentityAsync(string token, CancellationToken ct = default)
    {
        var tok = (token ?? "").Trim();
        if (string.IsNullOrWhiteSpace(tok))
            return new BotIdentity(false, "", "", "Bot token is empty.");
        try
        {
            using var resp = await Http.GetAsync($"https://api.telegram.org/bot{tok}/getMe", ct).ConfigureAwait(false);
            var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (!ok)
            {
                var desc = root.TryGetProperty("description", out var d) ? d.ToString() : $"HTTP {(int)resp.StatusCode}";
                return new BotIdentity(false, "", "", desc);
            }
            var res = root.GetProperty("result");
            var user = res.TryGetProperty("username", out var u) ? u.ToString() : "";
            var name = res.TryGetProperty("first_name", out var n) ? n.ToString() : "";
            return new BotIdentity(true, user, name, null);
        }
        catch (Exception ex)
        {
            return new BotIdentity(false, "", "", ex.Message);
        }
    }

    public static async Task<(string? ChatId, string? Error)> DetectChatIdAsync(string token, CancellationToken ct = default)
    {
        var tok = (token ?? "").Trim();
        if (string.IsNullOrWhiteSpace(tok))
            return (null, "Enter a bot token first.");
        try
        {
            using var _ = await Http.PostAsync(
                $"https://api.telegram.org/bot{tok}/deleteWebhook",
                new FormUrlEncodedContent(Array.Empty<KeyValuePair<string, string>>()),
                ct).ConfigureAwait(false);
            using var resp = await Http.GetAsync($"https://api.telegram.org/bot{tok}/getUpdates", ct).ConfigureAwait(false);
            var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            if (!root.TryGetProperty("ok", out var o) || o.ValueKind != JsonValueKind.True)
            {
                var desc = root.TryGetProperty("description", out var d) ? d.ToString() : $"HTTP {(int)resp.StatusCode}";
                return (null, desc);
            }
            if (root.TryGetProperty("result", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                for (var i = arr.GetArrayLength() - 1; i >= 0; i--)
                {
                    var item = arr[i];
                    if (item.TryGetProperty("message", out var msg)
                        && msg.TryGetProperty("chat", out var chat)
                        && chat.TryGetProperty("id", out var idEl))
                        return (idEl.ToString(), null);
                }
            }
            return (null, "No messages found — send /start to your bot in Telegram, then click Detect again.");
        }
        catch (Exception ex)
        {
            return (null, ex.Message);
        }
    }

    public static async Task<SendResult> SendMessageAsync(
        string token,
        string chatId,
        string htmlText,
        CancellationToken ct = default)
    {
        var tok = (token ?? "").Trim();
        var chat = (chatId ?? "").Trim();
        if (string.IsNullOrWhiteSpace(tok) || string.IsNullOrWhiteSpace(chat))
            return new SendResult(false, "Telegram bot token and chat ID are required.");
        try
        {
            using var content = new FormUrlEncodedContent(
            [
                new KeyValuePair<string, string>("chat_id", chat),
                new KeyValuePair<string, string>("text", htmlText),
                new KeyValuePair<string, string>("parse_mode", "HTML"),
            ]);
            using var resp = await Http.PostAsync($"https://api.telegram.org/bot{tok}/sendMessage", content, ct)
                .ConfigureAwait(false);
            var body = await resp.Content.ReadAsStringAsync(ct).ConfigureAwait(false);
            using var doc = JsonDocument.Parse(body);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == JsonValueKind.True;
            if (ok)
                return new SendResult(true, null);
            var desc = root.TryGetProperty("description", out var d)
                ? d.ToString()
                : $"HTTP {(int)resp.StatusCode}";
            return new SendResult(false, desc);
        }
        catch (Exception ex)
        {
            return new SendResult(false, ex.Message);
        }
    }
}
