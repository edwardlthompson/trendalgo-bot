namespace TrendAlgo.Shell.Models;

public sealed class AlertRow
{
    public string Kind { get; init; } = "";
    public string Pair { get; init; } = "";
    public string Reason { get; init; } = "";
    public string At { get; init; } = "";
}
