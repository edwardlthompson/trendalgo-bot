using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Persist LTS board DataGrid column widths under the device profile.</summary>
public static class BoardColumnWidthStore
{
    private const string FileName = "shell_board_column_widths.json";

    public static IReadOnlyDictionary<string, double> Load()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        if (!File.Exists(path))
            return new Dictionary<string, double>(StringComparer.Ordinal);
        try
        {
            var raw = JsonSerializer.Deserialize<Dictionary<string, double>>(File.ReadAllText(path));
            return raw is null
                ? new Dictionary<string, double>(StringComparer.Ordinal)
                : new Dictionary<string, double>(raw, StringComparer.Ordinal);
        }
        catch
        {
            return new Dictionary<string, double>(StringComparer.Ordinal);
        }
    }

    public static void Save(IReadOnlyDictionary<string, double> widths)
    {
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        File.WriteAllText(path, JsonSerializer.Serialize(widths));
    }
}
