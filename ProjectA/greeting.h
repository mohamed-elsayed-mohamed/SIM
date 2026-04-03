#pragma once

#ifdef PROJECTA_EXPORTS
#define PROJECTA_API __declspec(dllexport)
#else
#define PROJECTA_API __declspec(dllimport)
#endif

extern "C" {
    // Returns a greeting string formatted with fmt.
    // Memory is owned by ProjectA — callers must NOT free it.
    PROJECTA_API const char* GetGreeting();
}
