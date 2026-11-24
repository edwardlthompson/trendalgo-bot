namespace TrendAlgo.Shell.Services;

public static class ProfilePaths
{
    public static string DeviceRoot
    {
        get
        {
            var env = Environment.GetEnvironmentVariable("TRENDALGO_DEVICE_DIR");
            if (!string.IsNullOrWhiteSpace(env))
                return env;
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                ".trendalgo",
                "device");
        }
    }

    public static string ResultsDb => Path.Combine(DeviceRoot, "results.db");
    public static string Handshake => Path.Combine(DeviceRoot, "engine_ipc.json");
}
