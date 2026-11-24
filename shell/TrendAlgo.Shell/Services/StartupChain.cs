using System.Diagnostics;
using System.Text.Json;
using Avalonia.Controls;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell.Services;

/// <summary>Crash review → update/donate (PySide app._offer_startup_extras).</summary>
public static class StartupChain
{
    public static async Task RunAsync(Window owner)
    {
        try
        {
            var client = new DeskSurfaceClient();
            using var doc = client.Fetch("startup", "crypto");
            var root = doc.RootElement;
            var copy = root.TryGetProperty("copy", out var c) ? c : default;
            if (root.TryGetProperty("crash", out var crash) && crash.ValueKind == JsonValueKind.Object)
            {
                var dlg = new CrashReviewWindow();
                dlg.Bind(
                    Str(copy, "crash_body", "A crash was saved on this PC. Nothing was sent."),
                    Str(crash, "message"),
                    Str(crash, "stack"),
                    Str(copy, "crash_clear", "Clear saved crash"),
                    Str(copy, "crash_keep", "Keep for later"));
                var cleared = await dlg.ShowDialog<bool?>(owner);
                if (cleared == true)
                    client.AckStartup("clear_crash");
            }

            if (!root.TryGetProperty("prompt", out var prompt) || prompt.ValueKind != JsonValueKind.Object)
                return;

            var kind = Str(prompt, "kind");
            var version = Str(prompt, "version");
            var current = Str(root, "version");
            var launch = new LaunchPromptWindow();
            if (kind == "donate")
            {
                launch.BindDonate(
                    Str(copy, "donate_prompt"),
                    Str(copy, "donate_accept", "Donate"),
                    Str(copy, "donate_later", "Not now"));
                var accepted = await launch.ShowDialog<bool?>(owner);
                if (accepted == true)
                    OpenUrl(Str(prompt, "donate_url"));
                client.AckStartup("donate", current);
            }
            else if (kind == "update")
            {
                launch.BindUpdate(
                    $"A newer installer ({version}) is available.",
                    Str(prompt, "changelog"),
                    Str(copy, "update_download", "Download and install"),
                    Str(copy, "update_later", "Later"));
                var accepted = await launch.ShowDialog<bool?>(owner);
                if (accepted == true)
                    OpenUrl(Str(prompt, "url"));
                else
                    client.AckStartup("update", version, dismissed: true);
            }
        }
        catch
        {
            // Startup extras are best-effort — never block the shell.
        }
    }

    private static void OpenUrl(string url)
    {
        if (string.IsNullOrWhiteSpace(url)
            || !url.StartsWith("https://", StringComparison.OrdinalIgnoreCase))
            return;
        try
        {
            Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true });
        }
        catch
        {
            /* ignore */
        }
    }

    private static string Str(JsonElement el, string key, string fallback = "")
    {
        if (el.ValueKind != JsonValueKind.Object)
            return fallback;
        return el.TryGetProperty(key, out var p) && p.ValueKind != JsonValueKind.Null
            ? p.ToString()
            : fallback;
    }
}
