using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;

namespace TrendAlgo.Shell.Controls;

/// <summary>Sell→Neutral→Buy spectrum with tick — mirrors PySide ScoreSpectrum.</summary>
public sealed class ScoreSpectrumCell : Control
{
    public const double BuyThreshold = 0.35;

    public static readonly StyledProperty<double> ScoreProperty =
        AvaloniaProperty.Register<ScoreSpectrumCell, double>(nameof(Score));

    private static readonly IBrush SellBrush = new SolidColorBrush(Color.Parse("#DC2626"));
    private static readonly IBrush NeutralBrush = new SolidColorBrush(Color.Parse("#64748B"));
    private static readonly IBrush BuyBrush = new SolidColorBrush(Color.Parse("#16A34A"));
    private static readonly IPen TickPen = new Pen(Brushes.White, 2);

    public double Score
    {
        get => GetValue(ScoreProperty);
        set => SetValue(ScoreProperty, value);
    }

    static ScoreSpectrumCell()
    {
        AffectsRender<ScoreSpectrumCell>(ScoreProperty);
        MinHeightProperty.OverrideDefaultValue<ScoreSpectrumCell>(18);
        MinWidthProperty.OverrideDefaultValue<ScoreSpectrumCell>(60);
    }

    public static double ScoreToFrac(double score) =>
        Math.Clamp((score + 2.0) / 4.0, 0.0, 1.0);

    public static double SpectrumTickX(double width, double score, double margin = 2.0)
    {
        var trackW = Math.Max(1.0, width - 2 * margin);
        return margin + ScoreToFrac(score) * trackW;
    }

    public override void Render(DrawingContext context)
    {
        var w = Bounds.Width;
        var h = Bounds.Height;
        var track = new Rect(2, 4, Math.Max(1, w - 4), Math.Max(1, h - 8));
        var sellEnd = ScoreToFrac(-BuyThreshold);
        var buyStart = ScoreToFrac(BuyThreshold);
        DrawZone(context, track, 0, sellEnd, SellBrush);
        DrawZone(context, track, sellEnd, buyStart, NeutralBrush);
        DrawZone(context, track, buyStart, 1.0, BuyBrush);
        var tx = track.X + ScoreToFrac(Score) * track.Width;
        context.DrawLine(TickPen, new Point(tx, track.Y - 2), new Point(tx, track.Bottom + 2));
    }

    private static void DrawZone(DrawingContext ctx, Rect track, double lo, double hi, IBrush brush)
    {
        var x = track.X + lo * track.Width;
        var width = Math.Max(1.0, (hi - lo) * track.Width);
        ctx.DrawRectangle(brush, null, new Rect(x, track.Y, width, track.Height), 3, 3);
    }
}
