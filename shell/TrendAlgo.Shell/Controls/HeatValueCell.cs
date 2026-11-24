using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.VisualTree;

namespace TrendAlgo.Shell.Controls;

/// <summary>Numeric board cell with optional rank heat background and click shortcuts.</summary>
public sealed class HeatValueCell : Border
{
    public static readonly StyledProperty<string?> TextProperty =
        AvaloniaProperty.Register<HeatValueCell, string?>(nameof(Text));

    public static readonly StyledProperty<string?> HeatHexProperty =
        AvaloniaProperty.Register<HeatValueCell, string?>(nameof(HeatHex));

    public static readonly StyledProperty<bool> OpensResultsProperty =
        AvaloniaProperty.Register<HeatValueCell, bool>(nameof(OpensResults));

    public static readonly StyledProperty<string?> OpensChartWindowProperty =
        AvaloniaProperty.Register<HeatValueCell, string?>(nameof(OpensChartWindow));

    private readonly TextBlock _label = new()
    {
        HorizontalAlignment = Avalonia.Layout.HorizontalAlignment.Right,
        VerticalAlignment = Avalonia.Layout.VerticalAlignment.Center,
        Margin = new Thickness(4, 0),
        FontSize = 12,
    };

    public string? Text
    {
        get => GetValue(TextProperty);
        set => SetValue(TextProperty, value);
    }

    public string? HeatHex
    {
        get => GetValue(HeatHexProperty);
        set => SetValue(HeatHexProperty, value);
    }

    public bool OpensResults
    {
        get => GetValue(OpensResultsProperty);
        set => SetValue(OpensResultsProperty, value);
    }

    public string? OpensChartWindow
    {
        get => GetValue(OpensChartWindowProperty);
        set => SetValue(OpensChartWindowProperty, value);
    }

    private bool HasClickAction => OpensResults || !string.IsNullOrWhiteSpace(OpensChartWindow);

    static HeatValueCell()
    {
        TextProperty.Changed.AddClassHandler<HeatValueCell>((c, e) =>
            c._label.Text = e.NewValue as string ?? "");
        HeatHexProperty.Changed.AddClassHandler<HeatValueCell>((c, _) => c.ApplyHeat());
        OpensResultsProperty.Changed.AddClassHandler<HeatValueCell>((c, _) => c.UpdateCursor());
        OpensChartWindowProperty.Changed.AddClassHandler<HeatValueCell>((c, _) => c.UpdateCursor());
    }

    private void UpdateCursor() =>
        Cursor = HasClickAction ? new Cursor(StandardCursorType.Hand) : Cursor.Default;

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (!HasClickAction || !e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
            return;
        if (DataContext is not Models.OpportunityBoardRow row)
            return;
        for (Visual? v = this; v is not null; v = v.GetVisualParent())
        {
            if (v is DataGrid grid)
            {
                grid.SelectedItem = row;
                break;
            }
        }
        e.Pointer.Capture(this);
        e.Handled = true;
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        if (Equals(e.Pointer.Captured, this))
            e.Pointer.Capture(null);
        if (!HasClickAction || e.InitialPressMouseButton != MouseButton.Left)
            return;
        if (!new Rect(Bounds.Size).Contains(e.GetPosition(this)))
            return;
        if (DataContext is not Models.OpportunityBoardRow row)
            return;
        for (Visual? v = this; v is not null; v = v.GetVisualParent())
        {
            if (v is Window { DataContext: ViewModels.MainViewModel vm })
            {
                if (OpensResults)
                    Avalonia.Threading.Dispatcher.UIThread.Post(() => vm.RequestBoardResults(row));
                else if (!string.IsNullOrWhiteSpace(OpensChartWindow))
                {
                    var key = OpensChartWindow;
                    Avalonia.Threading.Dispatcher.UIThread.Post(() => vm.RequestBoardChart(row, key));
                }
                e.Handled = true;
                return;
            }
        }
    }

    public HeatValueCell()
    {
        Child = _label;
        CornerRadius = new CornerRadius(2);
        ApplyHeat();
    }

    private void ApplyHeat()
    {
        if (string.IsNullOrWhiteSpace(HeatHex) || !Color.TryParse(HeatHex, out var color))
        {
            Background = Brushes.Transparent;
            _label.Foreground = Brushes.White;
            return;
        }
        Background = new SolidColorBrush(color);
        var luminance = (0.299 * color.R + 0.587 * color.G + 0.114 * color.B) / 255.0;
        _label.Foreground = luminance > 0.45 ? Brushes.Black : Brushes.White;
    }
}
