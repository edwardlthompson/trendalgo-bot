using System.Runtime.Versioning;
using Microsoft.Win32;

namespace TrendAlgo.Shell.Services;

/// <summary>HKCU Run key — mirrors <c>trendalgo.device.autostart</c>.</summary>
public static class AutostartRegistry
{
    public const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    public const string ValueName = "TrendAlgoBot";

    public static bool IsEnabled()
    {
        if (!OperatingSystem.IsWindows())
            return false;
        return IsEnabledWindows();
    }

    public static void SetEnabled(bool enabled, string? command = null)
    {
        if (!OperatingSystem.IsWindows())
            return;
        SetEnabledWindows(enabled, command);
    }

    [SupportedOSPlatform("windows")]
    private static bool IsEnabledWindows()
    {
        try
        {
            using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: false);
            return key?.GetValue(ValueName) is not null;
        }
        catch
        {
            return false;
        }
    }

    [SupportedOSPlatform("windows")]
    private static void SetEnabledWindows(bool enabled, string? command)
    {
        try
        {
            if (!enabled)
            {
                using var key = Registry.CurrentUser.OpenSubKey(RunKey, writable: true);
                try
                {
                    key?.DeleteValue(ValueName, throwOnMissingValue: false);
                }
                catch
                {
                    /* missing ok */
                }
                return;
            }

            using var key2 = Registry.CurrentUser.CreateSubKey(RunKey);
            key2?.SetValue(ValueName, command ?? DefaultCommand(), RegistryValueKind.String);
        }
        catch
        {
            // Registry write failed (policy) — ignore.
        }
    }

    public static string DefaultCommand()
    {
        var exe = Environment.ProcessPath;
        if (!string.IsNullOrWhiteSpace(exe) && File.Exists(exe))
            return $"\"{exe}\"";
        // Source-first: prefer launch-device.ps1 via powershellw when present.
        var repo = FindRepoRoot();
        var launch = Path.Combine(repo, "scripts", "packaging", "launch-device.ps1");
        if (File.Exists(launch))
            return $"powershell.exe -NoProfile -WindowStyle Hidden -File \"{launch}\"";
        return $"\"{Environment.GetCommandLineArgs()[0]}\"";
    }

    private static string FindRepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
                return dir.FullName;
            dir = dir.Parent;
        }
        return Directory.GetCurrentDirectory();
    }
}
