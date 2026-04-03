#include "bridge.h"
#include "../ProjectA/greeting.h"
#include <nlohmann/json.hpp>
#include <string>

// Static buffer — safe for single-threaded P/Invoke callers.
static std::string g_json;

extern "C" PROJECTB_API const char* GetJsonGreeting()
{
    // Call ProjectA to get the raw greeting string.
    const char* greeting = GetGreeting();

    // Serialize it into a JSON object via nlohmann-json.
    nlohmann::json j;
    j["greeting"] = greeting;
    j["source"]   = "ProjectB";

    g_json = j.dump();
    return g_json.c_str();
}
