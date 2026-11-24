using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using TrendAlgo.Shell.Services;
using TrendAlgo.Shell.ViewModels;
using TrendAlgo.Shell.Views;

namespace TrendAlgo.Shell;

public partial class App : Application
{
    private ShellTray? _tray;

    public override void Initialize()
    {
        AvaloniaXamlLoader.Load(this);
    }

    public override void OnFrameworkInitializationCompleted()
    {
        ShellTheme.ApplyFromSettings();
        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            var vm = new MainViewModel();
            var main = new MainWindow { DataContext = vm };
            desktop.MainWindow = main;
            desktop.ShutdownMode = ShutdownMode.OnExplicitShutdown;
            _tray = new ShellTray(main, vm);
            main.SetTray(_tray);
            desktop.Exit += (_, _) => _tray?.Dispose();
            main.Opened += async (_, _) =>
            {
                await StartupChain.RunAsync(main);
            };
        }

        base.OnFrameworkInitializationCompleted();
    }
}
