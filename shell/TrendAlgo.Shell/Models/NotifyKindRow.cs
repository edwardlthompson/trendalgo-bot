using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class NotifyKindRow : ObservableObject
{
    [ObservableProperty] private string _id = "";
    [ObservableProperty] private string _label = "";
    [ObservableProperty] private bool _windows;
    [ObservableProperty] private bool _telegram;
}
