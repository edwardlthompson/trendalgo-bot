using System.Diagnostics;
using System.Text;

namespace TrendAlgo.Shell.Services;

/// <summary>OS toast via PowerShell WinRT (Qt showMessage parity; no WinForms clash).</summary>
public static class WindowsTrayToast
{
    public static void Show(string title, string body)
    {
        try
        {
            var t = Escape(string.IsNullOrWhiteSpace(title) ? "TrendAlgo" : title);
            var b = Escape(string.IsNullOrWhiteSpace(body) ? " " : body);
            var script = new StringBuilder();
            script.Append("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; ");
            script.Append("[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null; ");
            script.Append("$template = '<toast><visual><binding template=\"ToastGeneric\">");
            script.Append("<text>").Append(t).Append("</text>");
            script.Append("<text>").Append(b).Append("</text>");
            script.Append("</binding></visual></toast>'; ");
            script.Append("$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; $xml.LoadXml($template); ");
            script.Append("$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); ");
            script.Append("[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('TrendAlgo.Shell').Show($toast);");

            Process.Start(new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = "-NoProfile -NonInteractive -WindowStyle Hidden -Command " + Quote(script.ToString()),
                UseShellExecute = false,
                CreateNoWindow = true,
            })?.Dispose();
        }
        catch
        {
            // Toast APIs unavailable — ignore.
        }
    }

    private static string Escape(string value) =>
        value.Replace("&", "&amp;", StringComparison.Ordinal)
            .Replace("<", "&lt;", StringComparison.Ordinal)
            .Replace(">", "&gt;", StringComparison.Ordinal)
            .Replace("\"", "&quot;", StringComparison.Ordinal)
            .Replace("'", "''", StringComparison.Ordinal);

    private static string Quote(string value) =>
        "\"" + value.Replace("\"", "\\\"", StringComparison.Ordinal) + "\"";
}
