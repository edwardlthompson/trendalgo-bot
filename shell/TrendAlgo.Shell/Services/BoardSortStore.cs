using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Persist LTS board DataGrid sort column + direction under the device profile.</summary>
public static class BoardSortStore
{
    private const string FileName = "shell_board_sort.json";

    public sealed record State(string ColumnKey, bool Ascending);

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

    public static void Save(string columnKey, bool ascending)
    {
        if (string.IsNullOrWhiteSpace(columnKey))
            return;
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        File.WriteAllText(
            path,
            JsonSerializer.Serialize(new State(columnKey, ascending)));
    }
}
