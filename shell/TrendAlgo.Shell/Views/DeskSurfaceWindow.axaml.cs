using System.Collections.ObjectModel;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using Avalonia.Data;
using Avalonia.Interactivity;
using Avalonia.Media;
using TrendAlgo.Shell.Controls;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Views;

public partial class DeskSurfaceWindow : Window
{
    private readonly List<SurfaceGridRow> _all = new();
    private Func<SurfaceGridRow?, Task>? _onGlossary;
    private Func<SurfaceGridRow?, Task>? _onCreateBot;
    private Func<Task>? _onSharePng;

    public DeskSurfaceWindow()
    {
        InitializeComponent();
    }

    public void SetNote(string note) => NoteText.Text = note;

    public void Bind(
        string title,
        IEnumerable<SurfaceGridRow> rows,
        string note,
        string? disclaimer = null,
        (string, string, string, string, string)? headers = null,
        bool enableFilter = false,
        Func<SurfaceGridRow?, Task>? onGlossary = null,
        Func<SurfaceGridRow?, Task>? onCreateBot = null,
        Func<Task>? onSharePng = null,
        bool heatNetColumn = false)
    {
        Title = title;
        NoteText.Text = note;
        _all.Clear();
        _all.AddRange(rows);
        _onGlossary = onGlossary;
        _onCreateBot = onCreateBot;
        _onSharePng = onSharePng;
        ActionBar.IsVisible = onGlossary is not null || onCreateBot is not null || onSharePng is not null;
        CreateBotBtn.IsVisible = onCreateBot is not null;
        SharePngBtn.IsVisible = onSharePng is not null;
        GlossaryBtn.IsVisible = onGlossary is not null;
        FilterBox.IsVisible = enableFilter;
        FilterBox.Text = "";
        if (!string.IsNullOrWhiteSpace(disclaimer))
        {
            DisclaimerText.Text = disclaimer;
            DisclaimerText.IsVisible = true;
        }
        if (headers is { } h && Grid.Columns.Count >= 5)
        {
            SetHeader(0, h.Item1);
            SetHeader(1, h.Item2);
            SetHeader(2, h.Item3);
            SetHeader(3, h.Item4);
            SetHeader(4, h.Item5);
        }
        if (heatNetColumn)
            UseHeatNetColumn();
        ApplyFilter();
    }

    private void UseHeatNetColumn()
    {
        if (Grid.Columns.Count < 2)
            return;
        var headerText = HeaderText(Grid.Columns[1]) ?? "Net %";
        Grid.Columns.RemoveAt(1);
        var col = new DataGridTemplateColumn
        {
            Header = NoWrapHeader(headerText),
            Width = DataGridLength.Auto,
            CellTemplate = new FuncDataTemplate<SurfaceGridRow>((row, _) =>
            {
                var cell = new HeatValueCell
                {
                    [!HeatValueCell.TextProperty] = new Binding(nameof(SurfaceGridRow.Col2)),
                    [!HeatValueCell.HeatHexProperty] = new Binding(nameof(SurfaceGridRow.HeatHex)),
                };
                return cell;
            }, true),
        };
        Grid.Columns.Insert(1, col);
    }

    private void OnFilterChanged(object? sender, TextChangedEventArgs e) => ApplyFilter();

    private async void OnGlossary(object? sender, RoutedEventArgs e)
    {
        if (_onGlossary is null)
            return;
        await _onGlossary(Grid.SelectedItem as SurfaceGridRow);
    }

    private async void OnCreateBot(object? sender, RoutedEventArgs e)
    {
        if (_onCreateBot is null)
            return;
        await _onCreateBot(Grid.SelectedItem as SurfaceGridRow);
    }

    private async void OnSharePng(object? sender, RoutedEventArgs e)
    {
        if (_onSharePng is null)
            return;
        await _onSharePng();
    }

    private void ApplyFilter()
    {
        var q = FilterBox.Text?.Trim() ?? "";
        IEnumerable<SurfaceGridRow> view = _all;
        if (!string.IsNullOrEmpty(q))
        {
            view = _all.Where(r =>
                (r.Col1?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                || (r.Col2?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                || (r.Col5?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false)
                || (r.Role?.Contains(q, StringComparison.OrdinalIgnoreCase) ?? false));
        }
        Grid.ItemsSource = new ObservableCollection<SurfaceGridRow>(view);
    }

    private void SetHeader(int index, string text) =>
        Grid.Columns[index].Header = NoWrapHeader(text);

    private static string? HeaderText(DataGridColumn col) =>
        col.Header switch
        {
            TextBlock tb => tb.Text,
            string s => s,
            _ => null,
        };

    private static TextBlock NoWrapHeader(string text) =>
        new()
        {
            Text = text,
            TextWrapping = TextWrapping.NoWrap,
            TextTrimming = TextTrimming.None,
        };
}
