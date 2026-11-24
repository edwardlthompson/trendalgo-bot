using System.Collections.ObjectModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Media;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Views;

public partial class ChartSurfaceWindow : Window
{
    private IReadOnlyList<double> _closes = Array.Empty<double>();
    private IReadOnlyList<(double O, double H, double L, double C)> _ohlc =
        Array.Empty<(double, double, double, double)>();
    private IReadOnlyList<(string Side, double Price, int Index)> _trades =
        Array.Empty<(string, double, int)>();

    public ChartSurfaceWindow()
    {
        InitializeComponent();
    }

    public void Bind(
        string title,
        string stats,
        string note,
        IEnumerable<SurfaceGridRow> rows,
        IReadOnlyList<double> closes,
        IReadOnlyList<(double O, double H, double L, double C)>? ohlc = null,
        IReadOnlyList<(string Side, double Price, int Index)>? trades = null)
    {
        Title = title;
        StatsText.Text = stats;
        NoteText.Text = note;
        _closes = closes;
        _ohlc = ohlc ?? Array.Empty<(double, double, double, double)>();
        _trades = trades ?? Array.Empty<(string, double, int)>();
        Grid.ItemsSource = new ObservableCollection<SurfaceGridRow>(rows);
        DrawChart();
    }

    private void OnCanvasSized(object? sender, SizeChangedEventArgs e) => DrawChart();

    private void DrawChart()
    {
        SparkCanvas.Children.Clear();
        if (SparkCanvas.Bounds.Width < 8 || SparkCanvas.Bounds.Height < 8)
            return;
        if (_ohlc.Count >= 2)
            DrawCandles();
        else
            DrawSpark();
        DrawTradeMarkers();
    }

    private void DrawSpark()
    {
        if (_closes.Count < 2)
            return;
        var w = SparkCanvas.Bounds.Width;
        var h = SparkCanvas.Bounds.Height;
        var min = _closes.Min();
        var max = _closes.Max();
        var span = Math.Max(1e-9, max - min);
        var pts = new List<Point>(_closes.Count);
        for (var i = 0; i < _closes.Count; i++)
        {
            var x = i * (w - 2) / Math.Max(1, _closes.Count - 1);
            var y = h - 2 - ((_closes[i] - min) / span) * (h - 4);
            pts.Add(new Point(x + 1, y));
        }
        SparkCanvas.Children.Add(new Polyline
        {
            Points = new Points(pts),
            Stroke = new SolidColorBrush(Color.Parse("#5B9DFF")),
            StrokeThickness = 1.5,
        });
    }

    private void DrawCandles()
    {
        var w = SparkCanvas.Bounds.Width;
        var h = SparkCanvas.Bounds.Height;
        var min = _ohlc.Min(b => b.L);
        var max = _ohlc.Max(b => b.H);
        var span = Math.Max(1e-9, max - min);
        var n = _ohlc.Count;
        var slot = Math.Max(2.0, (w - 4) / n);
        var bodyW = Math.Max(1.0, slot * 0.6);

        double Y(double price) => h - 2 - ((price - min) / span) * (h - 4);

        for (var i = 0; i < n; i++)
        {
            var bar = _ohlc[i];
            var x = 2 + i * slot + slot / 2;
            var up = bar.C >= bar.O;
            var brush = new SolidColorBrush(Color.Parse(up ? "#3DDC97" : "#FF6B6B"));
            SparkCanvas.Children.Add(new Line
            {
                StartPoint = new Point(x, Y(bar.H)),
                EndPoint = new Point(x, Y(bar.L)),
                Stroke = brush,
                StrokeThickness = 1,
            });
            var top = Math.Min(Y(bar.O), Y(bar.C));
            var bodyH = Math.Max(1.0, Math.Abs(Y(bar.C) - Y(bar.O)));
            SparkCanvas.Children.Add(new Rectangle
            {
                Width = bodyW,
                Height = bodyH,
                Fill = brush,
                [Canvas.LeftProperty] = x - bodyW / 2,
                [Canvas.TopProperty] = top,
            });
        }
    }

    private void DrawTradeMarkers()
    {
        if (_trades.Count == 0)
            return;
        var w = SparkCanvas.Bounds.Width;
        var h = SparkCanvas.Bounds.Height;
        var prices = _ohlc.Count >= 2
            ? _ohlc.SelectMany(b => new[] { b.H, b.L }).ToList()
            : _closes.ToList();
        if (prices.Count < 2)
            return;
        var min = prices.Min();
        var max = prices.Max();
        var span = Math.Max(1e-9, max - min);
        var count = Math.Max(2, _ohlc.Count >= 2 ? _ohlc.Count : _closes.Count);
        double Y(double price) => h - 2 - ((price - min) / span) * (h - 4);

        foreach (var (side, price, index) in _trades)
        {
            var i = Math.Clamp(index, 0, count - 1);
            var x = 2 + i * (w - 4) / (count - 1.0);
            var y = Y(price);
            var entry = side.Equals("entry", StringComparison.OrdinalIgnoreCase);
            var color = Color.Parse(entry ? "#5B9DFF" : "#F5A623");
            SparkCanvas.Children.Add(new Ellipse
            {
                Width = 8,
                Height = 8,
                Fill = new SolidColorBrush(color),
                [Canvas.LeftProperty] = x - 4,
                [Canvas.TopProperty] = y - 4,
            });
        }
    }
}
