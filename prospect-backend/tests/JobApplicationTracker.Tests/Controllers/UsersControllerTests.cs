using System.Net;
using System.Net.Http.Json;

namespace JobApplicationTracker.Tests.Controllers;

public class UsersControllerTests : IClassFixture<TestWebApplicationFactory>, IAsyncLifetime
{
    private readonly HttpClient _client;
    private readonly TestWebApplicationFactory _factory;

    public UsersControllerTests(TestWebApplicationFactory factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    public Task InitializeAsync() { _factory.ResetDatabase(); return Task.CompletedTask; }
    public Task DisposeAsync() => Task.CompletedTask;

    [Fact]
    public async Task GetMe_ReturnsNotFound_WhenTheUserDoesNotExist()
    {
        // ResetDatabase seeds only IDs 1 and 2, so 999 exercises the null branch.
        TestCurrentUserService.CurrentUserId = 999;

        var response = await _client.GetAsync("/api/users/me");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task PutMe_PersistsCity()
    {
        TestCurrentUserService.CurrentUserId = 1;

        var put = await _client.PutAsJsonAsync("/api/users/me", new { city = "Sydney" });
        Assert.Equal(HttpStatusCode.OK, put.StatusCode);

        var body = await (await _client.GetAsync("/api/users/me")).Content.ReadAsStringAsync();
        Assert.Contains("Sydney", body);
    }

    [Fact]
    public async Task PutMe_TreatsBlankCityAsUnset()
    {
        TestCurrentUserService.CurrentUserId = 1;

        await _client.PutAsJsonAsync("/api/users/me", new { city = "Sydney" });
        await _client.PutAsJsonAsync("/api/users/me", new { city = "   " });

        var body = await (await _client.GetAsync("/api/users/me")).Content.ReadAsStringAsync();
        Assert.DoesNotContain("Sydney", body);
    }
}
