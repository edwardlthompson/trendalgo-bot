using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Platform;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Services;

/// <summary>Native tray: Show / Scanner / Run scan / Quit + balloon toasts.</summary>
public sealed class ShellTray
{
    private readonly TrayIcon _icon;
    private readonly Window _window;
    private readonly MainViewModel _vm;

    public ShellTray(Window window, MainViewModel vm)
    {
        _window = window;
        _vm = vm;
        var menu = new NativeMenu();
        menu.Add(Item("Show", ShowWindow));
        menu.Add(Item("Scanner (Crypto)", () =>
        {
            ShowWindow();
            _vm.NavigateCommand.Execute("crypto");
        }));
        menu.Add(Item("Run scan", () =>
        {
            ShowWindow();
            _vm.NavigateCommand.Execute("crypto");
            _vm.DeskRunScanCommand.Execute(null);
        }));
        menu.Add(new NativeMenuItemSeparator());
        menu.Add(Item("Quit", Quit));

        _icon = new TrayIcon
        {
            ToolTipText = "TrendAlgo Shell",
            IsVisible = true,
            Menu = menu,
        };
        try
        {
            _icon.Icon = new WindowIcon(
                AssetLoader.Open(new Uri("avares://TrendAlgo.Shell/Assets/app-icon.ico")));
        }
        catch
        {
            // tray still works without custom icon
        }
        _icon.Clicked += (_, _) => ShowWindow();
        _vm.AttachTrayToast(ShowMessage);
    }

    public bool CloseToTray { get; set; } = true;

    public void ShowMessage(string title, string body, string? kind = null)
    {
        if (kind is not null && !NotifyPrefsGate.AllowWindows(kind))
            return;
        WindowsTrayToast.Show(title, body);
        _vm.StatusText = $"{title}: {body}";
    }

    public void ShowHiddenMessage() =>
        ShowMessage("TrendAlgo Bot", "TrendAlgo is still running in the system tray.");

    public void Dispose()
    {
        _icon.IsVisible = false;
        _icon.Dispose();
    }

    private void ShowWindow()
    {
        _window.Show();
        _window.WindowState = WindowState.Normal;
        _window.Activate();
    }

    private void Quit()
    {
        CloseToTray = false;
        if (Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desk)
            desk.Shutdown();
        else
            _window.Close();
    }

    private static NativeMenuItem Item(string header, Action action)
    {
        var item = new NativeMenuItem(header);
        item.Click += (_, _) => action();
        return item;
    }
}
