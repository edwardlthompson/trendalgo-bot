using System.Text.Json;

namespace TrendAlgo.Shell.Services;

/// <summary>Persist MainWindow size/position under the device profile root.</summary>
public static class WindowGeometryStore
{
    private const string FileName = "shell_geometry.json";

    public sealed record Geometry(double X, double Y, double Width, double Height, string State);

    public static Geometry? Load()
    {
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        if (!File.Exists(path))
            return null;
        try
        {
            return JsonSerializer.Deserialize<Geometry>(File.ReadAllText(path));
        }
        catch
        {
            return null;
        }
    }

    public static void Save(Geometry geo)
    {
        Directory.CreateDirectory(ProfilePaths.DeviceRoot);
        var path = Path.Combine(ProfilePaths.DeviceRoot, FileName);
        File.WriteAllText(path, JsonSerializer.Serialize(geo));
    }
}
