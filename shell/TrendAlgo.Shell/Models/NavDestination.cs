using Avalonia;
using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

/// <summary>P0 parity map from docs/PRODUCT_SURFACE_INVENTORY.md §12.</summary>
public sealed partial class NavDestination : ObservableObject
{
    public NavDestination(
        string id,
        string label,
        string glyph,
        bool inMore = false,
        bool isSubItem = false,
        string? parentDesk = null)
    {
        Id = id;
        BaseLabel = label;
        Glyph = glyph;
        InMore = inMore;
        IsSubItem = isSubItem;
        ParentDesk = parentDesk;
        _label = label;
    }

    public string Id { get; }
    public string BaseLabel { get; }
    public string Glyph { get; }
    public bool InMore { get; }
    public bool IsSubItem { get; }
    public string? ParentDesk { get; }
    public Thickness Indent => IsSubItem ? new Thickness(16, 0, 0, 0) : new Thickness(0);

    [ObservableProperty] private string _label;
    [ObservableProperty] private bool _isVisible = true;

    public void SetDeskLoadPercent(int? pct)
    {
        Label = pct is { } p
            ? $"{BaseLabel} · {p}%"
            : BaseLabel;
    }

    public void SetDeskHeaderLabel(bool expanded, int? pct)
    {
        var arrow = expanded ? "▾" : "▸";
        Label = pct is { } p
            ? $"{arrow} {BaseLabel} · {p}%"
            : $"{arrow} {BaseLabel}";
    }
}
