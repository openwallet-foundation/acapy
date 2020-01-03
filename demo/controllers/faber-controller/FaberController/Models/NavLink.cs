using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace FaberController.Models
{
    public class NavLink
    {
        [JsonPropertyName("url")]
        public string Url { get; set; }

        [JsonPropertyName("label")]
        public string Label { get; set; }

        public override string ToString() => JsonSerializer.Serialize(this);
    }
}
