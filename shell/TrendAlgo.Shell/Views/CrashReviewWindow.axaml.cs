using Avalonia.Controls;
using Avalonia.Interactivity;

namespace TrendAlgo.Shell.Views;

public partial class CrashReviewWindow : Window
{
    public bool Cleared { get; private set; }

    public CrashReviewWindow()
    {
        InitializeComponent();
    }

    public void Bind(string body, string message, string stack, string clearLabel, string keepLabel)
    {
        BodyText.Text = body;
        DetailBox.Text = $"Message:\n{message}\n\nStack:\n{stack}";
        ClearBtn.Content = clearLabel;
        KeepBtn.Content = keepLabel;
    }

    private void OnClear(object? sender, RoutedEventArgs e)
    {
        Cleared = true;
        Close(true);
    }

    private void OnKeep(object? sender, RoutedEventArgs e) => Close(false);
}
