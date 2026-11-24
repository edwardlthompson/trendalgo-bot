using System.Diagnostics;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform.Storage;
using CommunityToolkit.Mvvm.Input;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private async Task DashboardExportHtmlReport()
    {
        try
        {
            var dest = await PickSaveFileAsync(
                $"portfolio-report-{DateTime.Now:yyyy-MM-dd}.html",
                "HTML Portfolio Report",
                ["*.html"]);
            if (dest is null)
            {
                StatusText = "Portfolio HTML report cancelled";
                return;
            }
            var reqPath = Path.Combine(ProfilePaths.DeviceRoot, "shell_portfolio_report.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(reqPath, $"{{\"kind\":\"html\",\"dest\":\"{EscapeJson(dest)}\"}}");
            using var doc = await _surfaces.ExportPortfolioReportAsync(reqPath);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == System.Text.Json.JsonValueKind.True;
            var outPath = root.TryGetProperty("path", out var p) ? p.ToString() : dest;
            if (!ok)
            {
                var err = root.TryGetProperty("error", out var e) ? e.ToString() : "export failed";
                StatusText = $"Portfolio report failed: {err}";
                return;
            }
            StatusText = $"Executive Portfolio Report → {outPath}";
            try
            {
                Process.Start(new ProcessStartInfo { FileName = outPath, UseShellExecute = true });
            }
            catch
            {
                /* non-fatal if browser launch is unavailable */
            }
        }
        catch (Exception ex)
        {
            StatusText = $"Portfolio report failed: {ex.Message}";
        }
    }

    [RelayCommand]
    private async Task DashboardExportCsv()
    {
        try
        {
            var dest = await PickSaveFileAsync(
                $"portfolio-holdings-{DateTime.Now:yyyy-MM-dd}.csv",
                "Holdings CSV",
                ["*.csv"]);
            if (dest is null)
            {
                StatusText = "Portfolio CSV export cancelled";
                return;
            }
            var reqPath = Path.Combine(ProfilePaths.DeviceRoot, "shell_portfolio_report.json");
            Directory.CreateDirectory(ProfilePaths.DeviceRoot);
            File.WriteAllText(reqPath, $"{{\"kind\":\"csv\",\"dest\":\"{EscapeJson(dest)}\"}}");
            using var doc = await _surfaces.ExportPortfolioReportAsync(reqPath);
            var root = doc.RootElement;
            var ok = root.TryGetProperty("ok", out var o) && o.ValueKind == System.Text.Json.JsonValueKind.True;
            var msg = root.TryGetProperty("message", out var m) ? m.ToString() : $"Exported → {dest}";
            StatusText = ok ? msg : $"CSV export failed: {(root.TryGetProperty("error", out var e) ? e.ToString() : "error")}";
        }
        catch (Exception ex)
        {
            StatusText = $"Portfolio CSV export failed: {ex.Message}";
        }
    }

    private static async Task<string?> PickSaveFileAsync(string suggestedName, string typeName, string[] patterns)
    {
        if (Avalonia.Application.Current?.ApplicationLifetime is not IClassicDesktopStyleApplicationLifetime
            {
                MainWindow: { } owner
            })
            return Path.Combine(ProfilePaths.DeviceRoot, "exports", suggestedName);

        var file = await owner.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = typeName,
            SuggestedFileName = suggestedName,
            FileTypeChoices = [new FilePickerFileType(typeName) { Patterns = patterns }],
        });
        return file?.Path.LocalPath;
    }
}
