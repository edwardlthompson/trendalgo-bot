using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization.Metadata;

namespace TrendAlgo.Shell.Services;

/// <summary>Safe JsonNode serialization for .NET 8 (TypeInfoResolver required before options freeze).</summary>
internal static class JsonNodeWrite
{
    private static readonly JsonSerializerOptions Indented = Create(writeIndented: true);
    private static readonly JsonSerializerOptions Compact = Create(writeIndented: false);

    private static JsonSerializerOptions Create(bool writeIndented) =>
        new()
        {
            WriteIndented = writeIndented,
            TypeInfoResolver = new DefaultJsonTypeInfoResolver(),
        };

    public static string ToIndented(JsonNode node) => node.ToJsonString(Indented);

    public static string ToCompact(JsonNode node) => node.ToJsonString(Compact);
}
