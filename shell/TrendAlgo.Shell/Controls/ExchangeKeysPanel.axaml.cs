using Avalonia.Controls;
using Avalonia.Interactivity;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Controls;

public partial class ExchangeKeysPanel : UserControl
{
    public ExchangeKeysPanel()
    {
        InitializeComponent();
    }

    private void OnVerifyRowClick(object? sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string id } && DataContext is MainViewModel vm)
            vm.VerifyExchangeRowCommand.Execute(id);
    }

    private void OnDeleteRowClick(object? sender, RoutedEventArgs e)
    {
        if (sender is Button { Tag: string id } && DataContext is MainViewModel vm)
            vm.DeleteExchangeRowCommand.Execute(id);
    }
}
