using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class CustomizeModuleItem : ObservableObject
{
    public string Id { get; init; } = "";
    public string Title { get; init; } = "";
    public string Category { get; init; } = "";

    [ObservableProperty]
    private bool _isChecked;
}
