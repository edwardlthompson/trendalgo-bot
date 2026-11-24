using Avalonia;
using System;
using System.Runtime.InteropServices;

namespace TrendAlgo.Shell;

sealed class Program
{
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int SetCurrentProcessExplicitAppUserModelID(string appID);

    [STAThread]
    public static void Main(string[] args)
    {
        if (OperatingSystem.IsWindows())
        {
            try
            {
                _ = SetCurrentProcessExplicitAppUserModelID("TrendAlgo.Bot.Shell");
            }
            catch
            {
                /* optional taskbar grouping */
            }
        }
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>()
            .UsePlatformDetect()
            .WithInterFont()
            .LogToTrace();
}
