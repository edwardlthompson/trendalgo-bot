using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class PrefToggleRow : ObservableObject
{
    [ObservableProperty] private string _id = "";
    [ObservableProperty] private bool _enabled = true;
    [ObservableProperty] private bool _visible = true;
}
