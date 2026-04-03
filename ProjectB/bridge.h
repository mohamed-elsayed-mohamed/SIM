#pragma once

#ifdef PROJECTB_EXPORTS
#define PROJECTB_API __declspec(dllexport)
#else
#define PROJECTB_API __declspec(dllimport)
#endif

extern "C" {
    // Returns a JSON string containing the greeting from ProjectA.
    // Example: {"greeting":"Hello from ProjectA v1.0.0!","source":"ProjectB"}
    // Memory is owned by ProjectB — callers must NOT free it.
    PROJECTB_API const char* GetJsonGreeting();
}
