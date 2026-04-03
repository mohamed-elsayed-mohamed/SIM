using Newtonsoft.Json.Linq;

namespace ProjectC;

/// <summary>
/// Public API surface of ProjectC.
/// Retrieves the greeting produced by the C++ chain (A → B) and
/// deserializes it from the JSON envelope added by ProjectB.
/// </summary>
public static class Greeter
{
    /// <summary>
    /// Returns the plain greeting string extracted from ProjectB's JSON payload.
    /// Example return value: "Hello from ProjectA v1.0.0!"
    /// </summary>
    public static string GetGreeting()
    {
        string json = NativeBridge.GetJsonGreetingManaged();

        // ProjectB wraps the greeting as: {"greeting":"...","source":"ProjectB"}
        JObject obj = JObject.Parse(json);
        string greeting = obj["greeting"]?.Value<string>()
                          ?? throw new InvalidOperationException($"Missing 'greeting' key in: {json}");

        return greeting;
    }
}
