namespace TrendAlgo.Shell.Models;

public sealed class CoinEventRow
{
    public int Index { get; init; }
    public string Date { get; init; } = "";
    public string Title { get; init; } = "";
    public string Source { get; init; } = "";
    public string Note { get; init; } = "";
    public string Url { get; init; } = "";
    /// <summary>0…1 along the spark; null = distribute by index.</summary>
    public double? MarkerFrac { get; init; }
}
