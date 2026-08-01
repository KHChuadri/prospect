namespace JobApplicationTracker.Models.Agent;

// Tables the Python agent owns. They are declared here — and only here — so
// that EF Core is the single source of truth for every table in this database.
//
// Nothing in the .NET application reads or writes them; they exist in the model
// purely so `dotnet ef migrations add` can generate their DDL. That is also why
// they are grouped in one file rather than following the one-class-per-file
// convention used for real domain models: these are schema declarations, not
// domain types, and keeping them together makes the distinction visible.
//
// Column names are snake_case to match the agent's hand-written SQL. See
// Data/AgentTablesConfiguration.cs — the mapping is explicit, not conventional,
// so renaming a property here does NOT silently rename a column the agent
// queries.

public class FollowUp
{
    public int Id { get; set; }
    public int AppId { get; set; }
    public int UserId { get; set; }
    public string ThreadId { get; set; } = string.Empty;
    public string Status { get; set; } = "pending";
    public string DraftSubject { get; set; } = string.Empty;
    public string DraftBody { get; set; } = string.Empty;
    public string? RecipientEmail { get; set; }
    public string Reason { get; set; } = string.Empty;
    public string? Error { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? DecidedAt { get; set; }
    public DateTime? SentAt { get; set; }
}

public class Resume
{
    public int UserId { get; set; }
    public string Text { get; set; } = string.Empty;
    public DateTime UpdatedAt { get; set; }
}

public class AppAi
{
    public int AppId { get; set; }
    public int UserId { get; set; }
    public string JdText { get; set; } = string.Empty;
    public string? MatchJson { get; set; }
    public string? OptimizedResume { get; set; }
    public DateTime UpdatedAt { get; set; }
}

public class Recommendation
{
    public int Id { get; set; }
    public int UserId { get; set; }
    public string SourceMessageId { get; set; } = string.Empty;
    public string SourceSender { get; set; } = string.Empty;
    public string Company { get; set; } = string.Empty;
    public string Role { get; set; } = string.Empty;
    public string? Location { get; set; }
    public string? Url { get; set; }
    public string RawSnippet { get; set; } = string.Empty;
    public string Status { get; set; } = "pending";
    public int? AcceptedApplicationId { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? DecidedAt { get; set; }
}

public class GmailSyncState
{
    public int UserId { get; set; }
    public DateTime LastPolledAt { get; set; }
}

public class Event
{
    public int Id { get; set; }
    public string SourceName { get; set; } = string.Empty;
    public string SourceUid { get; set; } = string.Empty;
    public string Url { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public DateTime? StartsAt { get; set; }
    public DateTime? EndsAt { get; set; }
    public string? Location { get; set; }
    public bool IsOnline { get; set; }
    public string[] Organizations { get; set; } = [];
    public string[] Topics { get; set; } = [];
    public string? EventType { get; set; }
    public string RawSnippet { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
}

public class UserEvent
{
    public int UserId { get; set; }
    public int EventId { get; set; }
    public string Status { get; set; } = string.Empty;
    public DateTime DecidedAt { get; set; }
}

public class EventsCrawlState
{
    public string SourceName { get; set; } = string.Empty;
    public DateTime LastCrawledAt { get; set; }
    public string? LastError { get; set; }
}
