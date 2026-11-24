using System.Diagnostics;
using Avalonia.Controls;
using Avalonia.Interactivity;

namespace TrendAlgo.Shell.Views;

public partial class FeedbackWindow : Window
{
    private readonly string _changelogUrl;

    public FeedbackWindow() : this("TrendAlgo", "", "", "")
    {
    }

    public FeedbackWindow(string versionLine, string body, string donate, string changelogUrl)
    {
        InitializeComponent();
        VersionText.Text = string.IsNullOrWhiteSpace(versionLine) ? "TrendAlgo Shell" : versionLine;
        BodyText.Text = body;
        DonateText.Text = donate;
        _changelogUrl = changelogUrl;
    }

    private void OnChangelog(object? sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_changelogUrl))
            return;
        try
        {
            Process.Start(new ProcessStartInfo(_changelogUrl) { UseShellExecute = true });
        }
        catch
        {
            // ignore browser launch failures
        }
    }

    private void OnClose(object? sender, RoutedEventArgs e) => Close();
}
