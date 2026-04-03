using Serilog;

namespace ProjectD;

/// <summary>
/// Top-level orchestration layer consumed by Project E (Unity).
/// Calls into Project C to retrieve the greeting, then logs it via Serilog.
/// </summary>
public static class Pipeline
{
    /// <summary>
    /// Runs the full greeting pipeline:
    ///   ProjectA (C++) → ProjectB (C++) → ProjectC (C#) → ProjectD (C#)
    /// Returns the greeting string so Unity can display it.
    /// </summary>
    public static string Run()
    {
        // Configure a console logger (works in both .NET 8 and Unity editor console).
        using var logger = new LoggerConfiguration()
            .WriteTo.Console(outputTemplate: "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}")
            .CreateLogger();

        logger.Information("Pipeline starting...");

        string greeting;
        try
        {
            greeting = ProjectC.Greeter.GetGreeting();
            logger.Information("Greeting received: {Greeting}", greeting);
        }
        catch (Exception ex)
        {
            logger.Error(ex, "Failed to retrieve greeting from ProjectC");
            throw;
        }

        logger.Information("Pipeline complete.");
        return greeting;
    }
}
