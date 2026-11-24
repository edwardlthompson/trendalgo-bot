using System.Globalization;
using System.Text.Json;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Media;

namespace TrendAlgo.Shell.Controls;

/// <summary>Native Avalonia Market Context module graphics mirroring PySide market_context_gfx.</summary>
public sealed class MarketContextCardGraphic : Control
{
    public const double BuyThreshold = 0.35;

    private static readonly IBrush UpBrush = new SolidColorBrush(Color.Parse("#3DDC97"));
    private static readonly IBrush DownBrush = new SolidColorBrush(Color.Parse("#FF6B6B"));
    private static readonly IBrush SlateBrush = new SolidColorBrush(Color.Parse("#64748B"));
    private static readonly IBrush TrackBrush = new SolidColorBrush(Color.Parse("#334155"));
    private static readonly IBrush AccentBrush = new SolidColorBrush(Color.Parse("#5B9DFF"));
    private static readonly IBrush BarGoodBrush = new SolidColorBrush(Color.Parse("#2563EB"));
    private static readonly IBrush LabelBrush = new SolidColorBrush(Color.Parse("#E5E7EB"));
    private static readonly IBrush MutedBrush = new SolidColorBrush(Color.Parse("#9CA3AF"));

    private string _signal = "Neutral";
    private double _score;
    private double? _lastPrice;
    private double? _rr1;
    private double? _rr2;
    private double? _vwapPct;
    private double? _pocPct;
    private double? _hiPct;
    private readonly List<(string Name, double Price)> _levels = new();

    public string Kind { get; set; } = "signal";

    static MarketContextCardGraphic()
    {
        MinHeightProperty.OverrideDefaultValue<MarketContextCardGraphic>(128);
        HorizontalAlignmentProperty.OverrideDefaultValue<MarketContextCardGraphic>(HorizontalAlignment.Stretch);
    }

    public void SetContext(JsonElement? ctx)
    {
        _signal = "Neutral";
        _score = 0;
        _lastPrice = null;
        _rr1 = null;
        _rr2 = null;
        _vwapPct = null;
        _pocPct = null;
        _hiPct = null;
        _levels.Clear();

        if (ctx is { ValueKind: JsonValueKind.Object } root)
        {
            _lastPrice = OptD(root, "last_price");
            if (root.TryGetProperty("consensus", out var cons) && cons.ValueKind == JsonValueKind.Object)
            {
                if (cons.TryGetProperty("signal", out var sg) && sg.ValueKind == JsonValueKind.String)
                    _signal = sg.GetString() ?? "Neutral";
                _score = OptD(cons, "score") ?? 0;
            }
            if (root.TryGetProperty("pivots", out var piv) && piv.ValueKind == JsonValueKind.Object
                && piv.TryGetProperty("levels", out var arr) && arr.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in arr.EnumerateArray())
                {
                    if (item.ValueKind != JsonValueKind.Object) continue;
                    var name = item.TryGetProperty("name", out var n) ? n.ToString() : "";
                    var px = OptD(item, "price");
                    if (px is not null) _levels.Add((name, px.Value));
                }
            }
            if (root.TryGetProperty("risk", out var risk) && risk.ValueKind == JsonValueKind.Object)
            {
                _rr1 = OptD(risk, "rr_to_r1");
                _rr2 = OptD(risk, "rr_to_r2");
            }
            if (root.TryGetProperty("structure", out var st) && st.ValueKind == JsonValueKind.Object)
            {
                _vwapPct = OptD(st, "vwap_dist_pct");
                _hiPct = OptD(st, "drawdown_from_high_pct");
                var poc = OptD(st, "poc");
                if (_lastPrice is > 0 && poc is > 0)
                    _pocPct = 100.0 * (_lastPrice.Value - poc.Value) / poc.Value;
            }
        }
        InvalidateVisual();
    }

    public override void Render(DrawingContext ctx)
    {
        var w = Bounds.Width;
        var h = Bounds.Height;
        if (w < 12 || h < 12) return;
        switch (Kind)
        {
            case "levels": DrawLevels(ctx, w, h); break;
            case "risk": DrawRisk(ctx, w, h); break;
            case "structure": DrawStructure(ctx, w, h); break;
            default: DrawSignal(ctx, w, h); break;
        }
    }

    private void DrawSignal(DrawingContext ctx, double w, double h)
    {
        var cx = w / 2.0;
        var cy = h - 34.0;
        var r = Math.Max(18.0, Math.Min(w * 0.38, h - 46.0));
        static double Deg(double s) => 90.0 - Math.Clamp(s / 2.0, -1.0, 1.0) * 90.0;
        DrawArcBand(ctx, cx, cy, r, Deg(-BuyThreshold), Deg(-2.0), DownBrush);
        DrawArcBand(ctx, cx, cy, r, Deg(BuyThreshold), Deg(-BuyThreshold), SlateBrush);
        DrawArcBand(ctx, cx, cy, r, Deg(2.0), Deg(BuyThreshold), UpBrush);

        foreach (var (deg, lbl) in new[] { (180.0, "Sell"), (90.0, "N"), (0.0, "Buy") })
        {
            var rad = deg * Math.PI / 180.0;
            var p1 = new Point(cx + Math.Cos(rad) * (r - 8), cy - Math.Sin(rad) * (r - 8));
            var p2 = new Point(cx + Math.Cos(rad) * (r + 6), cy - Math.Sin(rad) * (r + 6));
            ctx.DrawLine(new Pen(LabelBrush, 2), p1, p2);
            var ft = Txt(lbl, 9, MutedBrush);
            ctx.DrawText(ft, new Point(cx + Math.Cos(rad) * (r + 16) - ft.Width / 2, cy - Math.Sin(rad) * (r + 16) - ft.Height / 2));
        }

        var nrad = Deg(_score) * Math.PI / 180.0;
        var tip = new Point(cx + Math.Cos(nrad) * (r - 12), cy - Math.Sin(nrad) * (r - 12));
        var lPt = new Point(cx + Math.Cos(nrad + 1.45) * 7, cy - Math.Sin(nrad + 1.45) * 7);
        var rPt = new Point(cx + Math.Cos(nrad - 1.45) * 7, cy - Math.Sin(nrad - 1.45) * 7);
        var needleBrush = _signal == "Buy" ? UpBrush : (_signal == "Sell" ? DownBrush : SlateBrush);
        var geo = new StreamGeometry();
        using (var g = geo.Open()) { g.BeginFigure(tip, true); g.LineTo(lPt); g.LineTo(rPt); g.EndFigure(true); }
        ctx.DrawGeometry(needleBrush, null, geo);
        ctx.DrawEllipse(LabelBrush, null, new Point(cx, cy), 4.5, 4.5);

        var sigTxt = Txt(_signal, 12, LabelBrush, bold: true);
        ctx.DrawText(sigTxt, new Point((w - sigTxt.Width) / 2, h - 20));
    }

    private static void DrawArcBand(DrawingContext ctx, double cx, double cy, double r, double startDeg, double endDeg, IBrush brush)
    {
        if (endDeg <= startDeg) return;
        var geo = new StreamGeometry();
        const int steps = 16;
        using (var g = geo.Open())
        {
            for (var i = 0; i <= steps; i++)
            {
                var rad = (startDeg + (endDeg - startDeg) * i / steps) * Math.PI / 180.0;
                var pt = new Point(cx + Math.Cos(rad) * r, cy - Math.Sin(rad) * r);
                if (i == 0) g.BeginFigure(pt, false);
                else g.LineTo(pt);
            }
        }
        ctx.DrawGeometry(null, new Pen(brush, 10), geo);
    }

    private void DrawLevels(DrawingContext ctx, double w, double h)
    {
        if (_levels.Count == 0)
        {
            var dash = Txt("—", 12, MutedBrush);
            ctx.DrawText(dash, new Point((w - dash.Width) / 2, (h - dash.Height) / 2));
            return;
        }
        var lo = _levels.Min(v => v.Price);
        var hi = _levels.Max(v => v.Price);
        var span = Math.Max(hi - lo, 1e-9);
        var x = w * 0.62;
        double top = 12, bot = h - 12;
        ctx.DrawLine(new Pen(TrackBrush, 2), new Point(x, top), new Point(x, bot));
        foreach (var (name, price) in _levels)
        {
            var y = bot - (price - lo) / span * (bot - top);
            var col = name.StartsWith("R") ? UpBrush : (name.StartsWith("S") ? DownBrush : SlateBrush);
            ctx.DrawLine(new Pen(col, 2.5), new Point(x - 12, y), new Point(x + 12, y));
            var ft = Txt($"{name} {ShortPx(price)}", 9, LabelBrush);
            ctx.DrawText(ft, new Point(4, y - ft.Height / 2));
        }
        if (_lastPrice is { } lp)
        {
            var y = Math.Clamp(bot - (lp - lo) / span * (bot - top), top, bot);
            ctx.DrawEllipse(AccentBrush, null, new Point(x, y), 4.5, 4.5);
            var ft = Txt(ShortPx(lp), 9, AccentBrush, bold: true);
            ctx.DrawText(ft, new Point(x + 14, y - ft.Height / 2));
        }
    }

    private void DrawRisk(DrawingContext ctx, double w, double h)
    {
        var items = new[] { ("R1", _rr1), ("R2", _rr2) };
        var maxV = Math.Max(1.0, items.Where(i => i.Item2 is not null).Select(i => i.Item2!.Value).DefaultIfEmpty(1.0).Max());
        var barW = Math.Max(16.0, (w - 24) / 2);
        const double lblH = 18;
        for (var i = 0; i < items.Length; i++)
        {
            var (lbl, val) = items[i];
            var x = 8 + i * (barW + 8);
            var barH = val is { } v ? (h - 28 - lblH) * Math.Min(1.0, Math.Max(0.05, v / maxV)) : 4;
            var y = h - lblH - 8 - barH;
            var fill = val is >= 1.0 ? BarGoodBrush : TrackBrush;
            ctx.DrawRectangle(fill, new Pen(SlateBrush, 1), new Rect(x, y, barW, barH), 4, 4);
            var ft = Txt(val is { } rv ? $"{lbl} {rv:0.00}" : $"{lbl} —", 10, LabelBrush);
            ctx.DrawText(ft, new Point(x + (barW - ft.Width) / 2, h - lblH));
        }
    }

    private void DrawStructure(DrawingContext ctx, double w, double h)
    {
        var rows = new[] { ("VWAP", _vwapPct), ("POC", _pocPct), ("Hi", _hiPct) };
        var rowH = (h - 14) / 3.0;
        for (var i = 0; i < rows.Length; i++)
        {
            var (lbl, raw) = rows[i];
            var y = 6 + i * rowH;
            var ft = Txt(lbl, 9, MutedBrush);
            ctx.DrawText(ft, new Point(4, y + (rowH - ft.Height) / 2));
            var track = new Rect(46, y + rowH * 0.28, Math.Max(16, w - 54), Math.Max(6, rowH * 0.4));
            ctx.DrawRectangle(TrackBrush, null, track, 3, 3);
            var mid = track.Center.X;
            if (raw is { } pct)
            {
                var frac = Math.Clamp(pct / 5.0, -1.0, 1.0);
                var fw = Math.Abs(frac) * (track.Width / 2);
                var fill = frac >= 0
                    ? new Rect(mid, track.Y, fw, track.Height)
                    : new Rect(mid - fw, track.Y, fw, track.Height);
                ctx.DrawRectangle(frac >= 0 ? UpBrush : DownBrush, null, fill, 3, 3);
            }
            ctx.DrawLine(new Pen(SlateBrush, 1), new Point(mid, track.Y - 2), new Point(mid, track.Bottom + 2));
        }
    }

    private static FormattedText Txt(string s, double size, IBrush brush, bool bold = false) =>
        new(s, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
            bold ? new Typeface(Typeface.Default.FontFamily, FontStyle.Normal, FontWeight.SemiBold) : Typeface.Default,
            size, brush);

    private static double? OptD(JsonElement el, string key) =>
        el.TryGetProperty(key, out var p) && p.TryGetDouble(out var v) ? v : null;

    private static string ShortPx(double p) =>
        Math.Abs(p) >= 1000 ? p.ToString("N0", CultureInfo.InvariantCulture)
        : Math.Abs(p) >= 1 ? p.ToString("N2", CultureInfo.InvariantCulture)
        : p.ToString("0.0000", CultureInfo.InvariantCulture);
}
