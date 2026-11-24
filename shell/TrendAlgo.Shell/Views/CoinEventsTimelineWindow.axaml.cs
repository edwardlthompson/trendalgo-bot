using System.Collections.ObjectModel;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Interactivity;
using Avalonia.Media;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Views;

public partial class CoinEventsTimelineWindow : Window
{
    private IReadOnlyList<double> _closes = Array.Empty<double>();
    private ObservableCollection<CoinEventRow> _rows = new();

    public CoinEventsTimelineWindow()
    {
        InitializeComponent();
    }

    public void Bind(
        string title,
        string hint,
        string emptyCopy,
        IEnumerable<CoinEventRow> rows,
        IReadOnlyList<double> closes)
    {
        Title = title;
        HintText.Text = hint;
        _closes = closes ?? Array.Empty<double>();
        _rows = new ObservableCollection<CoinEventRow>(rows);
        Grid.ItemsSource = _rows;
        if (_closes.Count < 2)
        {
            EmptyChart.Text = string.IsNullOrWhiteSpace(emptyCopy)
                ? "No price series for timeline"
                : emptyCopy;
            EmptyChart.IsVisible = true;
        }
        else
            EmptyChart.IsVisible = false;
        DrawChart();
    }

    private void OnCanvasSized(object? sender, SizeChangedEventArgs e) => DrawChart();

    private void OnClose(object? sender, RoutedEventArgs e) => Close();

    private void DrawChart()
    {
        SparkCanvas.Children.Clear();
        if (_closes.Count < 2 || SparkCanvas.Bounds.Width < 8 || SparkCanvas.Bounds.Height < 8)
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

        var n = Math.Max(1, _rows.Count);
        for (var i = 0; i < _rows.Count; i++)
        {
            var frac = _rows[i].MarkerFrac ?? (n <= 1 ? 0.5 : (double)i / (n - 1));
            frac = Math.Clamp(frac, 0, 1);
            var x = 1 + frac * (w - 2);
            SparkCanvas.Children.Add(new Line
            {
                StartPoint = new Point(x, 2),
                EndPoint = new Point(x, h - 2),
                Stroke = new SolidColorBrush(Color.Parse("#88FFFFFF")),
                StrokeThickness = 1,
            });
            SparkCanvas.Children.Add(new Ellipse
            {
                Width = 8,
                Height = 8,
                Fill = new SolidColorBrush(Color.Parse("#5B9DFF")),
                [Canvas.LeftProperty] = x - 4,
                [Canvas.TopProperty] = h / 2 - 4,
            });
        }
    }
}
