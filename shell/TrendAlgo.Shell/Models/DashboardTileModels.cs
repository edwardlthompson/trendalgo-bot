using Avalonia.Media;
using Avalonia.Media.Imaging;
using TrendAlgo.Shell.Services;

namespace TrendAlgo.Shell.Models;

public sealed class DashboardPageTab
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public bool IsActive { get; init; }
    public IBrush BackgroundBrush => IsActive
        ? new SolidColorBrush(Color.Parse("#2563EB"))
        : new SolidColorBrush(Color.Parse("#1E293B"));
}

public sealed class DashboardChartPoint
{
    public string X { get; init; } = "";
    public double Y { get; init; }
}

public sealed class DashboardChartSeries
{
    public string Name { get; init; } = "";
    public string Color { get; init; } = "#3DDC97";
    public IReadOnlyList<DashboardChartPoint> Points { get; init; } = [];
}

public sealed class DashboardSliceItem
{
    public string Label { get; init; } = "";
    public double ValueUsd { get; init; }
    public double Pct { get; init; }
    public string Color { get; init; } = "#3DDC97";
}

public sealed class DashboardBarItem
{
    public string Label { get; init; } = "";
    public double Value { get; init; }
}

public sealed class DashboardCellItem
{
    public string Label { get; init; } = "";
    public double ValueUsd { get; init; }
    public double Pct { get; init; }
    public double ChangePct { get; init; }
}

public sealed class DashboardKpiItem
{
    public string Label { get; init; } = "";
    public string Value { get; init; } = "—";
    public int Sign { get; init; }
    public IBrush ValueBrush => Sign > 0
        ? new SolidColorBrush(Color.Parse("#3DDC97"))
        : Sign < 0
            ? new SolidColorBrush(Color.Parse("#FF6B6B"))
            : new SolidColorBrush(Color.Parse("#F8FAFC"));
}

public sealed class DashboardRankedItem
{
    public string Label { get; init; } = "";
    public string Value { get; init; } = "";
    public string Delta { get; init; } = "";
    public int Sign { get; init; }
    public IBrush DeltaBrush => Sign >= 0
        ? new SolidColorBrush(Color.Parse("#3DDC97"))
        : new SolidColorBrush(Color.Parse("#FF6B6B"));
}

public sealed class DashboardHoldingItem
{
    public string Asset { get; init; } = "";
    public string Venue { get; init; } = "";
    public string IconPath { get; init; } = "";
    public Bitmap? IconBitmap => CoinIconResolver.Load(Asset);
    public double Quantity { get; init; }
    public double PriceUsd { get; init; }
    public double? Change24hPct { get; init; }
    public double ValueUsd { get; init; }
    public double AllocationPct { get; init; }
    public double AvgBuyUsd { get; init; }
    public double PnlUsd { get; init; }
    public double PnlPct { get; init; }

    public string QuantityText => Quantity >= 1000 ? Quantity.ToString("N2") : Quantity.ToString("0.####");
    public string PriceText => PriceUsd >= 1 ? $"${PriceUsd:N2}" : $"${PriceUsd:0.0000}";
    public string ValueText => $"${ValueUsd:N2}";
    public string AllocText => $"{AllocationPct:0.0}%";
    public string AvgBuyText => AvgBuyUsd >= 1 ? $"${AvgBuyUsd:N2}" : AvgBuyUsd > 0 ? $"${AvgBuyUsd:0.0000}" : "—";
    public string ChangeText => Change24hPct is { } c ? $"{(c >= 0 ? "▲ " : "▼ ")}{c:+0.00;-0.00;0.00}%" : "—";
    public IBrush ChangeBrush => Change24hPct is { } c
        ? new SolidColorBrush(Color.Parse(c >= 0 ? "#3DDC97" : "#FF6B6B"))
        : new SolidColorBrush(Color.Parse("#94A3B8"));
    public string PnlText => $"{(PnlUsd >= 0 ? "+" : "-")}${Math.Abs(PnlUsd):N2} ({PnlPct:+0.00;-0.00;0.00}%)";
    public IBrush PnlBrush => new SolidColorBrush(Color.Parse(PnlUsd >= 0 ? "#3DDC97" : "#FF6B6B"));
}

public sealed class DashboardOrderItem
{
    public string Venue { get; init; } = "";
    public string Pair { get; init; } = "";
    public string Side { get; init; } = "";
    public string Price { get; init; } = "";
    public string Amount { get; init; } = "";
}
