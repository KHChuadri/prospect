using JobApplicationTracker.Models.Agent;
using Microsoft.EntityFrameworkCore;

namespace JobApplicationTracker.Data;

/// <summary>
/// Maps the Python agent's tables onto the EF model.
///
/// Every table and column name is stated explicitly rather than relying on EF's
/// naming conventions. The agent queries these tables with hand-written SQL, so
/// a column name here is a contract with code in another language that the
/// compiler cannot check. Explicit mapping means renaming a C# property is a
/// no-op on the database instead of a silent breaking change.
///
/// No query filters: unlike JobApplication and StatusTransition, nothing in the
/// .NET application queries these, so a tenant filter would have no effect and
/// would only mislead.
///
/// Every key, index and foreign key is given an EXPLICIT name matching what
/// Postgres generated for the agent's original CREATE TABLE statements
/// (events_pkey, events_source_name_source_uid_key, user_events_event_id_fkey,
/// and so on). Databases that predate this migration already carry those names.
/// If we let EF apply its own convention (PK_events, IX_events_...), the model
/// snapshot would disagree with every existing deployment, and the first future
/// migration to touch an index would try to alter an object that isn't there.
/// </summary>
public static class AgentTablesConfiguration
{
    public static void ConfigureAgentTables(this ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<FollowUp>(e =>
        {
            e.ToTable("follow_ups");
            e.HasKey(x => x.Id).HasName("follow_ups_pkey");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.AppId).HasColumnName("app_id");
            e.Property(x => x.UserId).HasColumnName("user_id");
            e.Property(x => x.ThreadId).HasColumnName("thread_id");
            e.Property(x => x.Status).HasColumnName("status").HasDefaultValue("pending");
            e.Property(x => x.DraftSubject).HasColumnName("draft_subject");
            e.Property(x => x.DraftBody).HasColumnName("draft_body");
            e.Property(x => x.RecipientEmail).HasColumnName("recipient_email");
            e.Property(x => x.Reason).HasColumnName("reason").HasDefaultValue("");
            e.Property(x => x.Error).HasColumnName("error");
            e.Property(x => x.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            e.Property(x => x.DecidedAt).HasColumnName("decided_at");
            e.Property(x => x.SentAt).HasColumnName("sent_at");
        });

        modelBuilder.Entity<Resume>(e =>
        {
            e.ToTable("resumes");
            e.HasKey(x => x.UserId).HasName("resumes_pkey");
            e.Property(x => x.UserId).HasColumnName("user_id").ValueGeneratedNever();
            e.Property(x => x.Text).HasColumnName("text");
            e.Property(x => x.UpdatedAt).HasColumnName("updated_at").HasDefaultValueSql("now()");
        });

        modelBuilder.Entity<AppAi>(e =>
        {
            e.ToTable("app_ai");
            e.HasKey(x => x.AppId).HasName("app_ai_pkey");
            e.Property(x => x.AppId).HasColumnName("app_id").ValueGeneratedNever();
            e.Property(x => x.UserId).HasColumnName("user_id");
            e.Property(x => x.JdText).HasColumnName("jd_text");
            e.Property(x => x.MatchJson).HasColumnName("match_json").HasColumnType("jsonb");
            e.Property(x => x.OptimizedResume).HasColumnName("optimized_resume");
            e.Property(x => x.UpdatedAt).HasColumnName("updated_at").HasDefaultValueSql("now()");
        });

        modelBuilder.Entity<Recommendation>(e =>
        {
            e.ToTable("recommendations");
            e.HasKey(x => x.Id).HasName("recommendations_pkey");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.UserId).HasColumnName("user_id");
            e.Property(x => x.SourceMessageId).HasColumnName("source_message_id");
            e.Property(x => x.SourceSender).HasColumnName("source_sender").HasDefaultValue("");
            e.Property(x => x.Company).HasColumnName("company");
            e.Property(x => x.Role).HasColumnName("role");
            e.Property(x => x.Location).HasColumnName("location");
            e.Property(x => x.Url).HasColumnName("url");
            e.Property(x => x.RawSnippet).HasColumnName("raw_snippet").HasDefaultValue("");
            e.Property(x => x.Status).HasColumnName("status").HasDefaultValue("pending");
            e.Property(x => x.AcceptedApplicationId).HasColumnName("accepted_application_id");
            e.Property(x => x.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            e.Property(x => x.DecidedAt).HasColumnName("decided_at");
            e.HasAlternateKey(x => x.SourceMessageId)
                .HasName("recommendations_source_message_id_key");
        });

        modelBuilder.Entity<GmailSyncState>(e =>
        {
            e.ToTable("gmail_sync_state");
            e.HasKey(x => x.UserId).HasName("gmail_sync_state_pkey");
            e.Property(x => x.UserId).HasColumnName("user_id").ValueGeneratedNever();
            e.Property(x => x.LastPolledAt).HasColumnName("last_polled_at");
        });

        modelBuilder.Entity<Event>(e =>
        {
            e.ToTable("events");
            e.HasKey(x => x.Id).HasName("events_pkey");
            e.Property(x => x.Id).HasColumnName("id");
            e.Property(x => x.SourceName).HasColumnName("source_name");
            e.Property(x => x.SourceUid).HasColumnName("source_uid");
            e.Property(x => x.Url).HasColumnName("url");
            e.Property(x => x.Title).HasColumnName("title");
            e.Property(x => x.Description).HasColumnName("description").HasDefaultValue("");
            e.Property(x => x.StartsAt).HasColumnName("starts_at");
            e.Property(x => x.EndsAt).HasColumnName("ends_at");
            e.Property(x => x.Location).HasColumnName("location");
            e.Property(x => x.IsOnline).HasColumnName("is_online").HasDefaultValue(false);
            // text[] — Npgsql maps string[] natively; the agent reads these as
            // Python lists, so they must stay arrays rather than becoming jsonb.
            e.Property(x => x.Organizations).HasColumnName("organizations")
                .HasColumnType("text[]").HasDefaultValueSql("'{}'");
            e.Property(x => x.Topics).HasColumnName("topics")
                .HasColumnType("text[]").HasDefaultValueSql("'{}'");
            e.Property(x => x.EventType).HasColumnName("event_type");
            e.Property(x => x.RawSnippet).HasColumnName("raw_snippet").HasDefaultValue("");
            e.Property(x => x.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
            // Gate 1 looks events up by this pair on every crawl.
            e.HasAlternateKey(x => new { x.SourceName, x.SourceUid })
                .HasName("events_source_name_source_uid_key");
            e.HasIndex(x => x.StartsAt).HasDatabaseName("events_starts_idx");
        });

        modelBuilder.Entity<UserEvent>(e =>
        {
            e.ToTable("user_events");
            e.HasKey(x => new { x.UserId, x.EventId }).HasName("user_events_pkey");
            e.Property(x => x.UserId).HasColumnName("user_id");
            e.Property(x => x.EventId).HasColumnName("event_id");
            e.Property(x => x.Status).HasColumnName("status");
            e.Property(x => x.DecidedAt).HasColumnName("decided_at").HasDefaultValueSql("now()");
            e.HasOne<Event>().WithMany()
                .HasForeignKey(x => x.EventId)
                .HasConstraintName("user_events_event_id_fkey")
                .OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<EventsCrawlState>(e =>
        {
            e.ToTable("events_crawl_state");
            e.HasKey(x => x.SourceName).HasName("events_crawl_state_pkey");
            e.Property(x => x.SourceName).HasColumnName("source_name");
            e.Property(x => x.LastCrawledAt).HasColumnName("last_crawled_at");
            e.Property(x => x.LastError).HasColumnName("last_error");
        });
    }
}
