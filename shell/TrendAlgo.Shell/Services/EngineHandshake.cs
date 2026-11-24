using System.Text.Json;
using TrendAlgo.Shell.Models;

namespace TrendAlgo.Shell.Services;

public static class EngineHandshake
{
    public static IpcHandshake? TryLoad(string? path = null)
    {
        var file = path ?? ProfilePaths.Handshake;
        if (!File.Exists(file))
            return null;
        var json = File.ReadAllText(file);
        return JsonSerializer.Deserialize<IpcHandshake>(json);
    }
}
