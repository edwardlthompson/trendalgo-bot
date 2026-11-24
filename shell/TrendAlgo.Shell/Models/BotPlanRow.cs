namespace TrendAlgo.Shell.Models;

public sealed class BotPlanRow
{
    public string Id { get; init; } = "";
    public string Name { get; init; } = "";
    public string Pair { get; init; } = "";
    public string Strategy { get; init; } = "";
    public string Timeframe { get; init; } = "";
    public string Stake { get; init; } = "";
    public string State { get; init; } = "";
    public bool Enabled { get; init; }
    public bool CanToggle { get; init; }
    public string Source { get; init; } = "";
}
