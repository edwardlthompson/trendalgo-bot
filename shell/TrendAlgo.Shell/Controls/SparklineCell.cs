using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.VisualTree;
using TrendAlgo.Shell.Models;
using TrendAlgo.Shell.ViewModels;

namespace TrendAlgo.Shell.Controls;

/// <summary>Painted sparkline: hi/lo guides, amber last-price line, gain path (PySide sparkline parity).</summary>
public sealed class SparklineCell : Control
{
    public static readonly StyledProperty<IReadOnlyList<double>?> ClosesProperty =
        AvaloniaProperty.Register<SparklineCell, IReadOnlyList<double>?>(nameof(Closes));

    public static readonly StyledProperty<bool> UpProperty =
        AvaloniaProperty.Register<SparklineCell, bool>(nameof(Up), defaultValue: true);

    public static readonly StyledProperty<double?> DistFromHighPctProperty =
        AvaloniaProperty.Register<SparklineCell, double?>(nameof(DistFromHighPct));

    public static readonly StyledProperty<string> WindowKeyProperty =
        AvaloniaProperty.Register<SparklineCell, string>(nameof(WindowKey), defaultValue: "30d");

    public string WindowKey
    {
        get => GetValue(WindowKeyProperty);
        set => SetValue(WindowKeyProperty, value);
    }

    private const int MaxPaint = 120;
    private static readonly IBrush GuideBrush = new SolidColorBrush(Color.Parse("#6B7280"));
    private static readonly IBrush LastPriceBrush = new SolidColorBrush(Color.Parse("#d97706")); // amber/brown
    private static readonly IBrush UpBrush = new SolidColorBrush(Color.Parse("#3DDC97"));
    private static readonly IBrush DownBrush = new SolidColorBrush(Color.Parse("#FF6B6B"));
    private static readonly IBrush DistBrush = new SolidColorBrush(Color.Parse("#9CA3AF"));

    public IReadOnlyList<double>? Closes
    {
        get => GetValue(ClosesProperty);
        set => SetValue(ClosesProperty, value);
    }

    public bool Up
    {
        get => GetValue(UpProperty);
        set => SetValue(UpProperty, value);
    }

    public double? DistFromHighPct
    {
        get => GetValue(DistFromHighPctProperty);
        set => SetValue(DistFromHighPctProperty, value);
    }

    static SparklineCell()
    {
        AffectsRender<SparklineCell>(ClosesProperty, UpProperty, DistFromHighPctProperty);
        MinHeightProperty.OverrideDefaultValue<SparklineCell>(32);
        MinWidthProperty.OverrideDefaultValue<SparklineCell>(60);
        CursorProperty.OverrideDefaultValue<SparklineCell>(new Cursor(StandardCursorType.Hand));
    }

    public override void Render(DrawingContext context)
    {
        var bounds = new Rect(Bounds.Size);
        context.FillRectangle(Brushes.Transparent, bounds);
        var closes = Closes;
        var distLabel = DistFromHighPct is { } d ? $"{d:0.0}%" : "—";
        var labelWidth = 40.0;
        var chartBounds = new Rect(0, 0, Math.Max(1, bounds.Width - labelWidth), bounds.Height);

        if (closes is null || closes.Count < 2)
        {
            DrawCentered(context, chartBounds, "—", GuideBrush);
            DrawDist(context, bounds, distLabel);
            return;
        }

        var series = Downsample(closes);
        var min = closes.Min();
        var max = closes.Max();
        var span = Math.Max(1e-9, max - min);
        var w = Math.Max(1, chartBounds.Width - 4);
        var h = Math.Max(1, chartBounds.Height - 4);
        var last = closes[^1];

        double YOf(double value) => 2 + h * (1.0 - (value - min) / span);

        // Hi / lo guides (PySide onSurfaceVariant)
        var guidePen = new Pen(GuideBrush, 1);
        context.DrawLine(guidePen, new Point(2, YOf(min)), new Point(2 + w, YOf(min)));
        context.DrawLine(guidePen, new Point(2, YOf(max)), new Point(2 + w, YOf(max)));

        // Current (last close) amber/brown reference line
        var lastPen = new Pen(LastPriceBrush, 1);
        context.DrawLine(lastPen, new Point(2, YOf(last)), new Point(2 + w, YOf(last)));

        var geo = new StreamGeometry();
        using (var ctx = geo.Open())
        {
            for (var i = 0; i < series.Count; i++)
            {
                var x = 2 + i * w / Math.Max(1, series.Count - 1);
                var y = YOf(series[i]);
                if (i == 0)
                    ctx.BeginFigure(new Point(x, y), false);
                else
                    ctx.LineTo(new Point(x, y));
            }
        }
        context.DrawGeometry(null, new Pen(Up ? UpBrush : DownBrush, 1.5), geo);
        DrawDist(context, bounds, distLabel);
    }

    private static void DrawDist(DrawingContext context, Rect bounds, string text)
    {
        var formatted = new FormattedText(
            text,
            System.Globalization.CultureInfo.InvariantCulture,
            FlowDirection.LeftToRight,
            Typeface.Default,
            10,
            DistBrush);
        var x = Math.Max(0, bounds.Width - formatted.Width - 2);
        var y = Math.Max(0, (bounds.Height - formatted.Height) / 2);
        context.DrawText(formatted, new Point(x, y));
    }

    private static void DrawCentered(DrawingContext context, Rect bounds, string text, IBrush brush)
    {
        var formatted = new FormattedText(
            text,
            System.Globalization.CultureInfo.InvariantCulture,
            FlowDirection.LeftToRight,
            Typeface.Default,
            11,
            brush);
        context.DrawText(
            formatted,
            new Point(
                (bounds.Width - formatted.Width) / 2,
                (bounds.Height - formatted.Height) / 2));
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (!e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
            return;
        if (DataContext is not OpportunityBoardRow row)
            return;
        var grid = FindAncestor<DataGrid>(this);
        if (grid is not null)
            grid.SelectedItem = row;
        e.Pointer.Capture(this);
        e.Handled = true;
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (Equals(e.Pointer.Captured, this))
            e.Pointer.Capture(null);
        if (e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (!new Rect(Bounds.Size).Contains(e.GetPosition(this)))
            return;
        if (DataContext is not OpportunityBoardRow row)
            return;
        var win = FindAncestor<Window>(this);
        if (win?.DataContext is MainViewModel vm)
        {
            var key = WindowKey;
            Avalonia.Threading.Dispatcher.UIThread.Post(() => vm.RequestBoardChart(row, key));
            e.Handled = true;
        }
    }

    private static IReadOnlyList<double> Downsample(IReadOnlyList<double> closes)
    {
        if (closes.Count <= MaxPaint)
            return closes;
        var step = Math.Max(1, closes.Count / MaxPaint);
        var list = new List<double>(MaxPaint + 1);
        for (var i = 0; i < closes.Count; i += step)
            list.Add(closes[i]);
        if (list[^1] != closes[^1])
            list.Add(closes[^1]);
        return list;
    }

    private static T? FindAncestor<T>(Visual? start) where T : Visual
    {
        for (var v = start; v is not null; v = v.GetVisualParent())
        {
            if (v is T hit)
                return hit;
        }
        return null;
    }
}
