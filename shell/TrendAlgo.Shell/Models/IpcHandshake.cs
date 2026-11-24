using System.Text.Json.Serialization;

namespace TrendAlgo.Shell.Models;

public sealed class IpcHandshake
{
    public const int ProtocolVersion = 1;
    public const int MinSchemaVersion = 1;

    [JsonPropertyName("protocol_version")]
    public int ProtocolVersionValue { get; set; }

    [JsonPropertyName("engine_version")]
    public string EngineVersion { get; set; } = "";

    [JsonPropertyName("schema_version")]
    public int SchemaVersion { get; set; }

    [JsonPropertyName("catalog_hash")]
    public string CatalogHash { get; set; } = "";

    [JsonPropertyName("results_db")]
    public string ResultsDb { get; set; } = "results.db";

    [JsonPropertyName("pid")]
    public int? Pid { get; set; }

    public bool IsCompatible =>
        ProtocolVersionValue == ProtocolVersion && SchemaVersion >= MinSchemaVersion;
}
