using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Windows toast allow-list from notify_prefs.json (PySide NotifyPrefs).</summary>
public static class NotifyPrefsGate
{
    public static bool AllowWindows(string kind)
    {
        var key = kind.Trim().ToLowerInvariant() switch
        {
            "logs" => "windows_logs",
            "entered" or "qualified" => "windows_entered",
            "left" or "watchlist" => "windows_left",
            "trades" or "trade" => "windows_trades",
            _ => "",
        };
        if (key.Length == 0)
            return true; // system toasts (tray hidden, scan done) always allowed
        var path = Path.Combine(ProfilePaths.DeviceRoot, "notify_prefs.json");
        if (!File.Exists(path))
            return key != "windows_logs"; // defaults: logs off, others on
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            if (doc.RootElement.TryGetProperty(key, out var p))
                return p.ValueKind == JsonValueKind.True;
            return key != "windows_logs";
        }
        catch
        {
            return key != "windows_logs";
        }
    }
}
