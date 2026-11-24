using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Threading;

namespace TrendAlgo.Shell.Views;

public partial class LoadingWindow : Window
{
    public LoadingWindow() : this("Loading…")
    {
    }

    public LoadingWindow(string message)
    {
        InitializeComponent();
        Title = message;
        MessageText.Text = message;
    }

    public static Window? MainOwner() =>
        Avalonia.Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime { MainWindow: { IsVisible: true } w }
            ? w
            : null;

    public static async Task<T> RunAsync<T>(Window? owner, string message, Func<Task<T>> work)
    {
        var dlg = new LoadingWindow(message);
        try
        {
            if (owner is { IsVisible: true })
                dlg.Show(owner);
            else
                dlg.Show();
            await Dispatcher.UIThread.InvokeAsync(() => { }, DispatcherPriority.Render);
            return await Task.Run(work);
        }
        finally
        {
            try { dlg.Close(); } catch { /* ignore */ }
        }
    }
}
