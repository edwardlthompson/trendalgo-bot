using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Remember last sidebar desk + Qualified/Watchlist/Logs tab.</summary>
public static class ShellNavStore
{
    private const string FileName = "shell_nav.json";

    public sealed record State(string NavId, string BoardTab);

    public static State? Load()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        if (!File.Exists(path))
            return null;
        try
        {
            return JsonSerializer.Deserialize<State>(File.ReadAllText(path));
        }
        catch
        {
            return null;
        }
    }

    public static void Save(string navId, string boardTab)
    {
        if (string.IsNullOrWhiteSpace(navId))
            return;
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        File.WriteAllText(
            path,
            JsonSerializer.Serialize(new State(navId.Trim(), (boardTab ?? "qualified").Trim())));
    }
}
