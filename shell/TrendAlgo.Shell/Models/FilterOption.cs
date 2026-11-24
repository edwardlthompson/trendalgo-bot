namespace TrendAlgo.Shell.Models;

public sealed record FilterOption(string Value, string Label)
{
    public override string ToString() => Label;
}
