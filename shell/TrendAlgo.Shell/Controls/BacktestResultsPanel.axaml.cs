using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Controls;

public partial class BacktestResultsPanel : UserControl
{
    private MainViewModel? _boundVm;

    public BacktestResultsPanel()
    {
        InitializeComponent();
        foreach (var col in Grid.Columns)
            SetNoWrapHeader(col);
        Grid.LayoutUpdated += (_, _) => ColumnFiltersBar.SyncToColumns(Grid);
        Loaded += (_, _) => ColumnFiltersBar.SyncToColumns(Grid);
        DataContextChanged += OnPanelDataContextChanged;
    }

    private void OnPanelDataContextChanged(object? sender, EventArgs e)
    {
        if (_boundVm is not null)
            _boundVm.BacktestMarketContextUpdated -= OnMarketContextUpdated;
        _boundVm = DataContext as MainViewModel;
        if (_boundVm is not null)
        {
            _boundVm.BacktestMarketContextUpdated += OnMarketContextUpdated;
            ApplyMarketContext(_boundVm.BacktestMarketContextJson);
        }
        else
        {
            ApplyMarketContext(null);
        }
    }

    private void OnMarketContextUpdated(JsonElement? ctx) => ApplyMarketContext(ctx);

    private void ApplyMarketContext(JsonElement? ctx)
    {
        GfxSignal.SetContext(ctx);
        GfxLevels.SetContext(ctx);
        GfxRisk.SetContext(ctx);
        GfxStructure.SetContext(ctx);
    }

    private void OnCreateBotRow(object? sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm && sender is Button { Tag: StrategyResultRow row })
        {
            Grid.SelectedItem = row;
            vm.BacktestCreateBotForResultRow(row);
        }
    }

    private void OnEventsCellPressed(object? sender, PointerPressedEventArgs e)
    {
        if (sender is Control ctrl && e.GetCurrentPoint(ctrl).Properties.IsLeftButtonPressed)
        {
            e.Pointer.Capture(ctrl);
            e.Handled = true;
        }
    }

    private void OnEventsCellReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (sender is Control ctrl && Equals(e.Pointer.Captured, ctrl))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (sender is Control c && !new Rect(c.Bounds.Size).Contains(e.GetPosition(c)))
            return;
        if (DataContext is MainViewModel vm)
        {
            e.Handled = true;
            vm.BacktestOpenEventsCommand.Execute(null);
        }
    }

    private static void SetNoWrapHeader(DataGridColumn col)
    {
        var title = col.Header switch
        {
            TextBlock tb => tb.Text ?? "",
            string s => s,
            _ => col.Header?.ToString() ?? "",
        };
        if (title.StartsWith("Avalonia.", StringComparison.Ordinal))
            title = string.IsNullOrWhiteSpace(col.SortMemberPath) ? "Column" : col.SortMemberPath;
        col.Header = new TextBlock
        {
            Text = title,
            TextWrapping = TextWrapping.NoWrap,
            TextTrimming = TextTrimming.CharacterEllipsis,
        };
    }
}
