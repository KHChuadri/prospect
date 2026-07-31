using System.Security.Claims;
using System.Text.Encodings.Web;
using JobApplicationTracker.Data;
using JobApplicationTracker.Services;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Testcontainers.PostgreSql;

namespace JobApplicationTracker.Tests;

public class TestWebApplicationFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .Build();

    public async Task InitializeAsync() => await _postgres.StartAsync();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            // Swap production DbContext registration for test container
            var descriptor = services.SingleOrDefault(d =>
                d.ServiceType == typeof(DbContextOptions<AppDbContext>));
            if (descriptor != null) services.Remove(descriptor);

            // Replace ICurrentUserService with a controllable stub
            var currentUserDescriptor = services.SingleOrDefault(d =>
                d.ServiceType == typeof(ICurrentUserService));
            if (currentUserDescriptor != null) services.Remove(currentUserDescriptor);
            services.AddScoped<ICurrentUserService, TestCurrentUserService>();

            // Replace JWT authentication with a no-op test handler
            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = "Test";
                options.DefaultChallengeScheme = "Test";
            }).AddScheme<AuthenticationSchemeOptions, TestAuthHandler>("Test", _ => { });

            services.AddDbContext<AppDbContext>(options =>
                options.UseNpgsql(_postgres.GetConnectionString()));
        });
    }

    public void ResetDatabase()
    {
        using var scope = Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        db.Database.EnsureCreated();
        db.Database.ExecuteSqlRaw(
            """
            TRUNCATE TABLE "StatusTransitions", "Notes", "JobApplications", "Users"
            RESTART IDENTITY CASCADE
            """);
        // Seed two users so tests can use IDs 1 and 2 without FK violations
        db.Database.ExecuteSqlRaw(
            """
            INSERT INTO "Users" ("Email", "PasswordHash")
            VALUES ('user1@test.com', 'x'), ('user2@test.com', 'x')
            """);
    }

    public new async Task DisposeAsync()
    {
        await _postgres.StopAsync();
        await base.DisposeAsync();
    }
}

// Controllable stub so tests can set the "current user" without needing a real JWT
public class TestCurrentUserService : ICurrentUserService
{
    public static int CurrentUserId { get; set; } = 0;
    public int UserId => CurrentUserId;
}

// Bypasses JWT validation in tests — always authenticates the current test user
public class TestAuthHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public TestAuthHandler(
        IOptionsMonitor<AuthenticationSchemeOptions> options,
        ILoggerFactory logger,
        UrlEncoder encoder) : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        var claims = new[] { new Claim(ClaimTypes.NameIdentifier, TestCurrentUserService.CurrentUserId.ToString()) };
        var identity = new ClaimsIdentity(claims, "Test");
        var ticket = new AuthenticationTicket(new ClaimsPrincipal(identity), "Test");
        return Task.FromResult(AuthenticateResult.Success(ticket));
    }
}