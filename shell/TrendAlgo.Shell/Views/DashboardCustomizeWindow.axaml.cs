using System.Collections.ObjectModel;
using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Interactivity;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Views;

public partial class DashboardCustomizeWindow : Window
{
    private readonly ObservableCollection<CustomizeModuleItem> _items = new();

    public DashboardCustomizeWindow()
    {
        InitializeComponent();
        ModuleList.ItemsSource = _items;
    }

    public IReadOnlyList<string> SelectedIds { get; private set; } = Array.Empty<string>();
    public int Cols { get; private set; } = 24;
    public int Rows { get; private set; } = 24;
    public bool ShowGrid { get; private set; }
    public bool Saved { get; private set; }

    public void Bind(JsonElement root)
    {
        _items.Clear();
        if (root.TryGetProperty("grid", out var grid) && grid.ValueKind == JsonValueKind.Object)
        {
            if (grid.TryGetProperty("cols", out var c) && c.TryGetInt32(out var cv))
                ColsBox.Value = cv;
            if (grid.TryGetProperty("rows", out var r) && r.TryGetInt32(out var rv))
                RowsBox.Value = rv;
            if (grid.TryGetProperty("show_grid", out var sg))
                ShowGridBox.IsChecked = sg.ValueKind == JsonValueKind.True;
        }
        if (root.TryGetProperty("customize", out var groups) && groups.ValueKind == JsonValueKind.Array)
        {
            foreach (var g in groups.EnumerateArray())
            {
                var cat = g.TryGetProperty("category", out var c) ? c.ToString() : "";
                if (!g.TryGetProperty("modules", out var mods) || mods.ValueKind != JsonValueKind.Array)
                    continue;
                foreach (var m in mods.EnumerateArray())
                {
                    _items.Add(new CustomizeModuleItem
                    {
                        Id = m.TryGetProperty("id", out var id) ? id.ToString() : "",
                        Title = cat.Length > 0
                            ? $"{(m.TryGetProperty("title", out var t) ? t.ToString() : "")} · {cat}"
                            : (m.TryGetProperty("title", out var t2) ? t2.ToString() : ""),
                        Category = cat,
                        IsChecked = m.TryGetProperty("checked", out var ch) && ch.ValueKind == JsonValueKind.True,
                    });
                }
            }
        }
    }

    private void OnSelectAll(object? sender, RoutedEventArgs e)
    {
        foreach (var item in _items)
            item.IsChecked = true;
    }

    private void OnClearAll(object? sender, RoutedEventArgs e)
    {
        foreach (var item in _items)
            item.IsChecked = false;
    }

    private void OnCancel(object? sender, RoutedEventArgs e)
    {
        Saved = false;
        Close();
    }

    private void OnSave(object? sender, RoutedEventArgs e)
    {
        SelectedIds = _items.Where(i => i.IsChecked).Select(i => i.Id).Where(id => id.Length > 0).ToList();
        Cols = (int)(ColsBox.Value ?? 24);
        Rows = (int)(RowsBox.Value ?? 24);
        ShowGrid = ShowGridBox.IsChecked == true;
        Saved = true;
        Close();
    }
}
