using Avalonia.Controls;
using Avalonia.Interactivity;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Controls;

public partial class DashboardPanel : UserControl
{
    public DashboardPanel()
    {
        InitializeComponent();
    }

    private void OnPageTabClick(object? sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string pageId } && DataContext is MainViewModel vm)
            vm.SelectDashboardPageCommand.Execute(pageId);
    }
}
