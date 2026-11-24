using System.Globalization;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Controls;

/// <summary>Native Avalonia anti-aliased portfolio charts (area, multi-line, bars, donut, treemap, gauge).</summary>
public sealed class DashboardChartCanvas : Control
{
    public static readonly StyledProperty<string> VisualKindProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, string>(nameof(VisualKind), "area_chart");

    public static readonly StyledProperty<IReadOnlyList<DashboardChartSeries>?> SeriesProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, IReadOnlyList<DashboardChartSeries>?>(nameof(Series));

    public static readonly StyledProperty<IReadOnlyList<DashboardSliceItem>?> SlicesProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, IReadOnlyList<DashboardSliceItem>?>(nameof(Slices));

    public static readonly StyledProperty<IReadOnlyList<DashboardBarItem>?> BarsProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, IReadOnlyList<DashboardBarItem>?>(nameof(Bars));

    public static readonly StyledProperty<IReadOnlyList<DashboardCellItem>?> CellsProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, IReadOnlyList<DashboardCellItem>?>(nameof(Cells));

    public static readonly StyledProperty<double> GaugeValueProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, double>(nameof(GaugeValue), 0.0);

    public static readonly StyledProperty<string> GaugeLabelProperty =
        AvaloniaProperty.Register<DashboardChartCanvas, string>(nameof(GaugeLabel), "");

    public string VisualKind
    {
        get => GetValue(VisualKindProperty);
        set => SetValue(VisualKindProperty, value);
    }

    public IReadOnlyList<DashboardChartSeries>? Series
    {
        get => GetValue(SeriesProperty);
        set => SetValue(SeriesProperty, value);
    }

    public IReadOnlyList<DashboardSliceItem>? Slices
    {
        get => GetValue(SlicesProperty);
        set => SetValue(SlicesProperty, value);
    }

    public IReadOnlyList<DashboardBarItem>? Bars
    {
        get => GetValue(BarsProperty);
        set => SetValue(BarsProperty, value);
    }

    public IReadOnlyList<DashboardCellItem>? Cells
    {
        get => GetValue(CellsProperty);
        set => SetValue(CellsProperty, value);
    }

    public double GaugeValue
    {
        get => GetValue(GaugeValueProperty);
        set => SetValue(GaugeValueProperty, value);
    }

    public string GaugeLabel
    {
        get => GetValue(GaugeLabelProperty);
        set => SetValue(GaugeLabelProperty, value);
    }

    static DashboardChartCanvas()
    {
        AffectsRender<DashboardChartCanvas>(
            VisualKindProperty,
            SeriesProperty,
            SlicesProperty,
            BarsProperty,
            CellsProperty,
            GaugeValueProperty,
            GaugeLabelProperty);
        HorizontalAlignmentProperty.OverrideDefaultValue<DashboardChartCanvas>(HorizontalAlignment.Stretch);
        VerticalAlignmentProperty.OverrideDefaultValue<DashboardChartCanvas>(VerticalAlignment.Stretch);
    }

    private static readonly IBrush MutedBrush = new SolidColorBrush(Color.Parse("#94A3B8"));
    private static readonly IBrush LabelBrush = new SolidColorBrush(Color.Parse("#E2E8F0"));
    private static readonly IBrush GridBrush = new SolidColorBrush(Color.Parse("#1E293B"));
    private static readonly IBrush UpBrush = new SolidColorBrush(Color.Parse("#3DDC97"));
    private static readonly IBrush DownBrush = new SolidColorBrush(Color.Parse("#FF6B6B"));

    public override void Render(DrawingContext ctx)
    {
        var w = Bounds.Width;
        var h = Bounds.Height;
        if (w < 24 || h < 20)
            return;

        switch (VisualKind)
        {
            case "donut":
                DrawDonut(ctx, w, h);
                break;
            case "treemap":
                DrawTreemap(ctx, w, h);
                break;
            case "alloc_bar":
                DrawAllocBar(ctx, w, h);
                break;
            case "bar_chart":
                DrawBars(ctx, w, h);
                break;
            case "gauge":
                DrawGauge(ctx, w, h);
                break;
            case "multi_line":
                DrawSeries(ctx, w, h, fillArea: false);
                break;
            default:
                DrawSeries(ctx, w, h, fillArea: true);
                break;
        }
    }

    private void DrawSeries(DrawingContext ctx, double w, double h, bool fillArea)
    {
        var seriesList = Series;
        if (seriesList is null || seriesList.Count == 0 || seriesList[0].Points.Count < 2)
        {
            DrawEmpty(ctx, w, h, "Awaiting 2+ snapshots");
            return;
        }
        var allY = seriesList.SelectMany(s => s.Points.Select(p => p.Y)).ToList();
        var lo = allY.Min();
        var hi = allY.Max();
        var span = Math.Max(hi - lo, 1e-6);
        var top = 10.0;
        var bot = h - 18.0;
        var left = 6.0;
        var right = w - 6.0;
        var pw = Math.Max(12.0, right - left);
        var ph = Math.Max(12.0, bot - top);

        ctx.DrawLine(new Pen(GridBrush, 1), new Point(left, top + ph * 0.5), new Point(right, top + ph * 0.5));

        foreach (var ser in seriesList)
        {
            var pts = ser.Points;
            if (pts.Count < 2) continue;
            var col = SafeColor(ser.Color, "#3DDC97");
            var mapped = new List<Point>(pts.Count);
            for (var i = 0; i < pts.Count; i++)
            {
                var px = left + (i / (double)(pts.Count - 1)) * pw;
                var py = bot - ((pts[i].Y - lo) / span) * ph;
                mapped.Add(new Point(px, py));
            }

            if (fillArea)
            {
                var fillGeo = new StreamGeometry();
                using (var g = fillGeo.Open())
                {
                    g.BeginFigure(new Point(mapped[0].X, bot), true);
                    foreach (var pt in mapped)
                        g.LineTo(pt);
                    g.LineTo(new Point(mapped[^1].X, bot));
                    g.EndFigure(true);
                }
                var grad = new LinearGradientBrush
                {
                    StartPoint = new RelativePoint(0, 0, RelativeUnit.Relative),
                    EndPoint = new RelativePoint(0, 1, RelativeUnit.Relative),
                    GradientStops =
                    {
                        new GradientStop(Color.FromArgb(88, col.R, col.G, col.B), 0),
                        new GradientStop(Color.FromArgb(6, col.R, col.G, col.B), 1),
                    },
                };
                ctx.DrawGeometry(grad, null, fillGeo);
            }

            var lineGeo = new StreamGeometry();
            using (var g = lineGeo.Open())
            {
                g.BeginFigure(mapped[0], false);
                for (var i = 1; i < mapped.Count; i++)
                    g.LineTo(mapped[i]);
            }
            ctx.DrawGeometry(null, new Pen(new SolidColorBrush(col), 2.2), lineGeo);
        }

        if (seriesList.Count > 1)
        {
            double lx = 8;
            foreach (var ser in seriesList.Take(3))
            {
                var col = new SolidColorBrush(SafeColor(ser.Color, "#3DDC97"));
                ctx.DrawRectangle(col, null, new Rect(lx, h - 13, 8, 8), 2, 2);
                var ft = Txt(ser.Name, 9.5, MutedBrush);
                ctx.DrawText(ft, new Point(lx + 11, h - 15));
                lx += ft.Width + 22;
            }
        }
    }

    private void DrawBars(DrawingContext ctx, double w, double h)
    {
        var bars = Bars;
        if (bars is null || bars.Count == 0)
        {
            DrawEmpty(ctx, w, h, "Daily bars build across sessions");
            return;
        }
        var maxAbs = Math.Max(bars.Max(b => Math.Abs(b.Value)), 1e-6);
        var midY = h * 0.5;
        var halfH = Math.Max(8.0, h * 0.42);
        ctx.DrawLine(new Pen(GridBrush, 1), new Point(4, midY), new Point(w - 4, midY));
        var slot = (w - 8) / bars.Count;
        var bw = Math.Max(3.0, slot * 0.68);
        for (var i = 0; i < bars.Count; i++)
        {
            var val = bars[i].Value;
            var bh = Math.Max(2.0, (Math.Abs(val) / maxAbs) * halfH);
            var bx = 4 + i * slot + (slot - bw) / 2.0;
            var by = val >= 0 ? midY - bh : midY;
            ctx.DrawRectangle(val >= 0 ? UpBrush : DownBrush, null, new Rect(bx, by, bw, bh), 2, 2);
        }
    }

    private void DrawDonut(DrawingContext ctx, double w, double h)
    {
        var slices = Slices;
        if (slices is null || slices.Count == 0)
        {
            DrawEmpty(ctx, w, h, "No allocation data");
            return;
        }
        var size = Math.Max(36.0, Math.Min(h - 12, w * 0.44));
        var r = size * 0.36;
        var stroke = Math.Max(8.0, size * 0.14);
        var cx = 12 + size * 0.5;
        var cy = h * 0.5;

        double startDeg = -90.0;
        var totalPct = Math.Max(slices.Sum(s => Math.Max(0.0, s.Pct)), 1e-6);
        foreach (var sl in slices)
        {
            var sweep = (Math.Max(0.0, sl.Pct) / totalPct) * 360.0;
            if (sweep < 0.8) continue;
            var col = new SolidColorBrush(SafeColor(sl.Color, "#3DDC97"));
            DrawArc(ctx, cx, cy, r, startDeg, startDeg + sweep, col, stroke);
            startDeg += sweep;
        }

        var lx = cx + size * 0.58;
        var availW = w - lx - 6;
        if (availW < 60) return;
        double ly = 6;
        foreach (var sl in slices.Take(6))
        {
            if (ly + 16 > h) break;
            var col = new SolidColorBrush(SafeColor(sl.Color, "#3DDC97"));
            ctx.DrawRectangle(col, null, new Rect(lx, ly + 3, 8, 8), 2, 2);
            var ft = Txt($"{sl.Label}  {sl.Pct:0.1}%", 10.5, LabelBrush);
            ctx.DrawText(ft, new Point(lx + 13, ly));
            ly += 18;
        }
    }

    private void DrawAllocBar(DrawingContext ctx, double w, double h)
    {
        var slices = Slices;
        if (slices is null || slices.Count == 0)
        {
            DrawEmpty(ctx, w, h, "No allocation data");
            return;
        }
        var total = Math.Max(slices.Sum(s => Math.Max(0.0, s.Pct)), 1e-6);
        var barRect = new Rect(4, 6, Math.Max(16, w - 8), Math.Min(16, h * 0.36));
        double x = barRect.X;
        foreach (var sl in slices)
        {
            var segW = Math.Max(2.0, (Math.Max(0.0, sl.Pct) / total) * barRect.Width);
            var col = new SolidColorBrush(SafeColor(sl.Color, "#3DDC97"));
            ctx.DrawRectangle(col, null, new Rect(x, barRect.Y, segW, barRect.Height), 2, 2);
            x += segW;
        }
        double lx = 4;
        var ly = barRect.Bottom + 6;
        foreach (var sl in slices.Take(5))
        {
            var col = new SolidColorBrush(SafeColor(sl.Color, "#3DDC97"));
            var ft = Txt($"{sl.Label} {sl.Pct:0.1}%", 10, MutedBrush);
            if (lx + ft.Width + 16 > w) break;
            ctx.DrawRectangle(col, null, new Rect(lx, ly + 3, 7, 7), 1.5, 1.5);
            ctx.DrawText(ft, new Point(lx + 10, ly));
            lx += ft.Width + 18;
        }
    }

    private void DrawTreemap(DrawingContext ctx, double w, double h)
    {
        var cells = Cells;
        if (cells is null || cells.Count == 0)
        {
            DrawEmpty(ctx, w, h, "No holdings");
            return;
        }
        var top = cells.Take(12).ToList();
        var rows = Math.Max(1, (int)Math.Ceiling(Math.Sqrt(top.Count)));
        var cols = Math.Max(1, (int)Math.Ceiling(top.Count / (double)rows));
        var cw = (w - (cols - 1) * 4.0) / cols;
        var ch = (h - (rows - 1) * 4.0) / rows;
        for (var i = 0; i < top.Count; i++)
        {
            var c = top[i];
            var r = i / cols;
            var colIdx = i % cols;
            var rect = new Rect(colIdx * (cw + 4), r * (ch + 4), cw, ch);
            var fill = c.ChangePct > 0.2
                ? Color.Parse("#14532D")
                : c.ChangePct < -0.2
                    ? Color.Parse("#7F1D1D")
                    : Color.Parse("#1E293B");
            var border = c.ChangePct > 0.2
                ? Color.Parse("#3DDC97")
                : c.ChangePct < -0.2
                    ? Color.Parse("#FF6B6B")
                    : Color.Parse("#334155");
            ctx.DrawRectangle(new SolidColorBrush(fill), new Pen(new SolidColorBrush(border), 1), rect, 6, 6);
            var ft1 = Txt(c.Label, 11, LabelBrush, bold: true);
            var ft2 = Txt($"{c.Pct:0.1}% · {c.ChangePct:+0.1;-0.1;0.0}%", 9.5, MutedBrush);
            ctx.DrawText(ft1, new Point(rect.X + 7, rect.Y + 5));
            if (ch >= 34)
                ctx.DrawText(ft2, new Point(rect.X + 7, rect.Y + 20));
        }
    }

    private void DrawGauge(DrawingContext ctx, double w, double h)
    {
        var cx = w * 0.5;
        var cy = h - 18.0;
        var r = Math.Max(18.0, Math.Min(w * 0.36, h - 28.0));
        DrawArc(ctx, cx, cy, r, 180, 360, GridBrush, 10);
        var frac = Math.Clamp(GaugeValue / 100.0, 0.0, 1.0);
        var col = frac >= 0.65 ? UpBrush : (frac >= 0.35 ? new SolidColorBrush(Color.Parse("#F59E0B")) : DownBrush);
        if (frac > 0.01)
            DrawArc(ctx, cx, cy, r, 180, 180 + frac * 180.0, col, 10);
        var lbl = string.IsNullOrWhiteSpace(GaugeLabel) ? $"{GaugeValue:0}%" : GaugeLabel;
        var ft = Txt(lbl, 11.5, LabelBrush, bold: true);
        ctx.DrawText(ft, new Point(cx - ft.Width * 0.5, cy - ft.Height - 2));
    }

    private static void DrawArc(DrawingContext ctx, double cx, double cy, double r, double startDeg, double endDeg, IBrush brush, double width)
    {
        const int steps = 28;
        var geo = new StreamGeometry();
        using (var g = geo.Open())
        {
            for (var i = 0; i <= steps; i++)
            {
                var rad = (startDeg + (endDeg - startDeg) * i / steps) * Math.PI / 180.0;
                var pt = new Point(cx + Math.Cos(rad) * r, cy + Math.Sin(rad) * r);
                if (i == 0) g.BeginFigure(pt, false);
                else g.LineTo(pt);
            }
        }
        ctx.DrawGeometry(null, new Pen(brush, width), geo);
    }

    private void DrawEmpty(DrawingContext ctx, double w, double h, string text)
    {
        var ft = Txt(text, 11, MutedBrush);
        ctx.DrawText(ft, new Point((w - ft.Width) * 0.5, (h - ft.Height) * 0.5));
    }

    private static Color SafeColor(string hex, string fallback) =>
        Color.TryParse(hex, out var c) ? c : Color.Parse(fallback);

    private static FormattedText Txt(string s, double size, IBrush brush, bool bold = false) =>
        new(s, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
            bold ? new Typeface(Typeface.Default.FontFamily, FontStyle.Normal, FontWeight.SemiBold) : Typeface.Default,
            size, brush);
}
