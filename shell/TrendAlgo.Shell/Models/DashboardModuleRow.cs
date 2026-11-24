using Avalonia.Media;

namespace TrendAlgo.Shell.Models;

public sealed class DashboardModuleRow
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public string Category { get; init; } = "";
    public string Span { get; init; } = "";
    public string Value { get; init; } = "";
    public string Detail { get; init; } = "";
    public string VisualKind { get; init; } = "kpi_grid";
    public string DeltaText { get; init; } = "";
    public int DeltaSign { get; init; }
    public double PixelLeft { get; init; }
    public double PixelTop { get; init; }
    public double PixelWidth { get; init; } = 120;
    public double PixelHeight { get; init; } = 80;
    public double GaugeValue { get; init; }
    public string GaugeLabel { get; init; } = "";

    public IReadOnlyList<DashboardChartSeries> Series { get; init; } = [];
    public IReadOnlyList<DashboardSliceItem> Slices { get; init; } = [];
    public IReadOnlyList<DashboardBarItem> Bars { get; init; } = [];
    public IReadOnlyList<DashboardCellItem> Cells { get; init; } = [];
    public IReadOnlyList<DashboardKpiItem> Kpis { get; init; } = [];
    public IReadOnlyList<DashboardRankedItem> RankedRows { get; init; } = [];
    public IReadOnlyList<DashboardHoldingItem> HoldingsRows { get; init; } = [];
    public IReadOnlyList<DashboardOrderItem> OrderRows { get; init; } = [];

    public bool HasDelta => !string.IsNullOrWhiteSpace(DeltaText);
    public IBrush DeltaBrush => DeltaSign > 0
        ? new SolidColorBrush(Color.Parse("#3DDC97"))
        : DeltaSign < 0
            ? new SolidColorBrush(Color.Parse("#FF6B6B"))
            : new SolidColorBrush(Color.Parse("#94A3B8"));

    public bool IsHoldingsTable => VisualKind == "holdings_table";
    public bool IsKpiGrid => VisualKind == "kpi_grid";
    public bool IsRankedList => VisualKind == "ranked_list";
    public bool IsOrdersTable => VisualKind == "orders_table";
    public bool IsChartVisual => !IsHoldingsTable && !IsKpiGrid && !IsRankedList && !IsOrdersTable;
    public bool HasChartInHero => VisualKind == "hero_worth" || IsChartVisual;
}
