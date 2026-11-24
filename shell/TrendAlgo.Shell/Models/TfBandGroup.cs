using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace TrendAlgo.Shell.Models;

public partial class TfBandGroup : ObservableObject
{
    [ObservableProperty] private string _id = "";
    [ObservableProperty] private string _title = "";
    [ObservableProperty] private string _note = "";
    [ObservableProperty] private bool _showNote;
    [ObservableProperty] private bool _showSeparatorAfter;

    public ObservableCollection<PrefToggleRow> Rows { get; } = new();
}
