#include "greeting.h"
#include <fmt/format.h>
#include <string>

// Static buffer — safe for single-threaded use by P/Invoke callers.
static std::string g_greeting;

extern "C" PROJECTA_API const char* GetGreeting()
{
    g_greeting = fmt::format("Hi from ProjectA v{}.{}.{}!", 1, 0, 0);
    return g_greeting.c_str();
}
