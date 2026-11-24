using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class DashboardMinRow : ObservableObject
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public string Category { get; init; } = "";
    public int DefaultW { get; init; }
    public int DefaultH { get; init; }
    public int MaxW { get; init; } = 24;
    public int MaxH { get; init; } = 16;

    [ObservableProperty]
    private int _minW;

    [ObservableProperty]
    private int _minH;
}
