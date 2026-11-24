using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class SettingsLayoutRow : ObservableObject
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public int MinW { get; init; }
    public int MinH { get; init; }

    [ObservableProperty] private int _col;
    [ObservableProperty] private int _row;
    [ObservableProperty] private int _w;
    [ObservableProperty] private int _h;
}
