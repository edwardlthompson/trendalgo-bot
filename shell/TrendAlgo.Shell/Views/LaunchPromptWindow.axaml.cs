using Avalonia.Controls;
using Avalonia.Interactivity;

namespace TrendAlgo.Shell.Views;

public partial class LaunchPromptWindow : Window
{
    public bool Accepted { get; private set; }

    public LaunchPromptWindow()
    {
        InitializeComponent();
    }

    public void BindDonate(string body, string accept, string later)
    {
        BodyText.Text = body;
        NotesScroll.IsVisible = false;
        AcceptBtn.Content = accept;
        LaterBtn.Content = later;
    }

    public void BindUpdate(string body, string changelog, string download, string later)
    {
        BodyText.Text = body;
        NotesText.Text = changelog ?? "";
        NotesScroll.IsVisible = !string.IsNullOrWhiteSpace(changelog);
        AcceptBtn.Content = download;
        LaterBtn.Content = later;
    }

    private void OnAccept(object? sender, RoutedEventArgs e)
    {
        Accepted = true;
        Close(true);
    }

    private void OnLater(object? sender, RoutedEventArgs e) => Close(false);
}
