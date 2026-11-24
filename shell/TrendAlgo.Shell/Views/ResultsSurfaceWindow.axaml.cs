using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Views;

public partial class ResultsSurfaceWindow : Window
{
    private readonly List<StrategyResultRow> _all = new();
    private readonly BacktestFilterState _filters = new();
    private Func<StrategyResultRow?, Task>? _onGlossary;
    private Func<StrategyResultRow?, Task>? _onCreateBot;
    private Func<Task>? _onSharePng;
    private Func<string, Task>? _onChart;
    private Func<Task>? _onEvents;

    public ResultsSurfaceWindow()
    {
        InitializeComponent();
        ColumnFiltersBar.DataContext = _filters;
        _filters.PropertyChanged += OnFiltersChanged;
        foreach (var col in Grid.Columns)
            SetNoWrapHeader(col);
        Grid.LayoutUpdated += (_, _) => ColumnFiltersBar.SyncToColumns(Grid);
        Loaded += (_, _) => ColumnFiltersBar.SyncToColumns(Grid);
    }

    public void BindNote(string note) => NoteText.Text = note;

    public void Bind(
        string title,
        IEnumerable<StrategyResultRow> rows,
        string note,
        string signal,
        string levels,
        string risk,
        string structure,
        JsonElement? marketContext = null,
        Func<StrategyResultRow?, Task>? onGlossary = null,
        Func<StrategyResultRow?, Task>? onCreateBot = null,
        Func<Task>? onSharePng = null,
        Func<string, Task>? onChart = null,
        Func<Task>? onEvents = null)
    {
        Title = title;
        NoteText.Text = note;
        McSignal.Text = string.IsNullOrWhiteSpace(signal) ? "Run a scan with candles to fill Market Context." : signal;
        McLevels.Text = string.IsNullOrWhiteSpace(levels) ? "—" : levels;
        McRisk.Text = string.IsNullOrWhiteSpace(risk) ? "—" : risk;
        McStructure.Text = string.IsNullOrWhiteSpace(structure) ? "—" : structure;
        GfxSignal.SetContext(marketContext);
        GfxLevels.SetContext(marketContext);
        GfxRisk.SetContext(marketContext);
        GfxStructure.SetContext(marketContext);
        _all.Clear();
        _all.AddRange(rows);
        _onGlossary = onGlossary;
        _onCreateBot = onCreateBot;
        _onSharePng = onSharePng;
        _onChart = onChart;
        _onEvents = onEvents;
        ApplyFilters();
        ColumnFiltersBar.SyncToColumns(Grid);
    }

    private void OnFiltersChanged(object? sender, PropertyChangedEventArgs e) => ApplyFilters();

    private void OnApplyFilters(object? sender, RoutedEventArgs e) => ApplyFilters();

    private void OnClearFilters(object? sender, RoutedEventArgs e)
    {
        _filters.IndicatorContains = "";
        _filters.Timeframe = "";
        _filters.ParamsContains = "";
        _filters.MinNetPct = "";
        _filters.MaxFees = "";
        _filters.MaxOpen = "";
        _filters.MinWins = "";
        _filters.MaxLosses = "";
        _filters.MinWinPct = "";
        _filters.MaxTslPct = "";
        _filters.MaxTslHits = "";
        _filters.MaxTslHitPct = "";
        _filters.MinStrength = "";
        ApplyFilters();
    }

    private async void OnGlossary(object? sender, RoutedEventArgs e)
    {
        if (_onGlossary is null)
            return;
        await _onGlossary(Grid.SelectedItem as StrategyResultRow);
    }

    private async void OnCreateBot(object? sender, RoutedEventArgs e)
    {
        if (_onCreateBot is null)
            return;
        await _onCreateBot(Grid.SelectedItem as StrategyResultRow);
    }

    private async void OnCreateBotRow(object? sender, RoutedEventArgs e)
    {
        if (_onCreateBot is null || sender is not Button { Tag: StrategyResultRow row })
            return;
        Grid.SelectedItem = row;
        await _onCreateBot(row);
    }

    private async void OnSharePng(object? sender, RoutedEventArgs e)
    {
        if (_onSharePng is null)
            return;
        await _onSharePng();
    }

    private async void OnChart7d(object? sender, RoutedEventArgs e)
    {
        if (_onChart is not null)
            await _onChart("7d");
    }

    private async void OnChart30d(object? sender, RoutedEventArgs e)
    {
        if (_onChart is not null)
            await _onChart("30d");
    }

    private async void OnEvents(object? sender, RoutedEventArgs e)
    {
        if (_onEvents is not null)
            await _onEvents();
    }

    private void OnEventsCellPressed(object? sender, PointerPressedEventArgs e)
    {
        if (sender is Control ctrl && e.GetCurrentPoint(ctrl).Properties.IsLeftButtonPressed)
        {
            e.Pointer.Capture(ctrl);
            e.Handled = true;
        }
    }

    private async void OnEventsCellReleased(object? sender, PointerReleasedEventArgs e)
    {
        if (sender is Control ctrl && Equals(e.Pointer.Captured, ctrl))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (sender is Control c && !new Rect(c.Bounds.Size).Contains(e.GetPosition(c)))
            return;
        if (_onEvents is not null)
        {
            e.Handled = true;
            await _onEvents();
        }
    }

    private void ApplyFilters()
    {
        var view = ResultsRowFilter.Apply(_all, _filters).ToList();
        Grid.ItemsSource = new ObservableCollection<StrategyResultRow>(view);
        NoteText.Text = view.Count == _all.Count
            ? $"{_all.Count} strategies"
            : $"{view.Count} of {_all.Count} strategies (filters applied)";
    }

    private static void SetNoWrapHeader(DataGridColumn col)
    {
        var title = col.Header switch
        {
            TextBlock tb => tb.Text ?? "",
            string s => s,
            _ => col.Header?.ToString() ?? "",
        };
        // Avoid "Avalonia.Controls.TextBlock" showing when ToString() is used later.
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
