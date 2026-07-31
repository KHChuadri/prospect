using System.Net;
using System.Net.Http.Json;
using JobApplicationTracker.Data;
using JobApplicationTracker.Tests.Helpers;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Testcontainers.PostgreSql;

namespace JobApplicationTracker.Tests.Controllers;

public class AuthControllerTests : IClassFixture<TestWebApplicationFactory>, IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly TestWebApplicationFactory _factory;

    public AuthControllerTests(TestWebApplicationFactory factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    public Task InitializeAsync() { _factory.ResetDatabase(); return Task.CompletedTask; }
    public Task DisposeAsync() => Task.CompletedTask;

    [Fact]
    public async Task Register_ReturnsTokens_OnSuccess()
    {
        var response = await _client.PostAsJsonAsync("/api/auth/register",
            new { email = "user@test.com", password = "Password123!" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var body = await response.Content.ReadAsStringAsync();
        Assert.Contains("accessToken", body);
    }

    [Fact]
    public async Task Register_ReturnsConflict_WhenEmailAlreadyExists()
    {
        await AuthHelper.RegisterAndLoginAsync(_client, "dup@test.com");

        var response = await _client.PostAsJsonAsync("/api/auth/register",
            new { email = "dup@test.com", password = "Password123!" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
    }

    [Fact]
    public async Task Login_ReturnsUnauthorized_WithBadPassword()
    {
        await AuthHelper.RegisterAndLoginAsync(_client, "user@test.com");

        var response = await _client.PostAsJsonAsync("/api/auth/login",
            new { email = "user@test.com", password = "wrongpassword" });

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task ProtectedRoute_Returns401_WithoutToken()
    {
        // The main TestWebApplicationFactory uses a test auth handler that always authenticates.
        // This test uses a real-JWT factory so that missing/invalid tokens return 401.
        await using var realJwtFactory = new RealJwtFactory();
        await realJwtFactory.InitializeAsync();
        realJwtFactory.ResetDatabase();

        var client = realJwtFactory.CreateClient();
        var response = await client.GetAsync("/api/applications");

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }
}

// ponytail: separate factory to test real JWT 401 — only replaces the DB connection, not auth
file class RealJwtFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16-alpine")
        .Build();

    public async Task InitializeAsync() => await _postgres.StartAsync();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            var descriptor = services.SingleOrDefault(d =>
                d.ServiceType == typeof(DbContextOptions<AppDbContext>));
            if (descriptor != null) services.Remove(descriptor);

            services.AddDbContext<AppDbContext>(options =>
                options.UseNpgsql(_postgres.GetConnectionString()));
        });
    }

    public void ResetDatabase()
    {
        using var scope = Services.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        db.Database.EnsureCreated();
    }

    public new async Task DisposeAsync()
    {
        await _postgres.StopAsync();
        await base.DisposeAsync();
    }
}
