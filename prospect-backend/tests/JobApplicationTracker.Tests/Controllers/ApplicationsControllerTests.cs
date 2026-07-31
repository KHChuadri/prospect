using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using JobApplicationTracker.Models;
using JobApplicationTracker.Tests.Helpers;

namespace JobApplicationTracker.Tests.Controllers;

public class ApplicationsControllerTests : IClassFixture<TestWebApplicationFactory>, IAsyncLifetime
{
    // API serializes enums as strings; test client must read them the same way.
    private static readonly JsonSerializerOptions JsonOpts =
        new(JsonSerializerDefaults.Web) { Converters = { new JsonStringEnumConverter() } };

    private readonly HttpClient _client;
    private readonly TestWebApplicationFactory _factory;

    public ApplicationsControllerTests(TestWebApplicationFactory factory)
    {
        _factory = factory;
        _client = factory.CreateClient();
    }

    public Task InitializeAsync() { _factory.ResetDatabase(); return Task.CompletedTask; }
    public Task DisposeAsync() => Task.CompletedTask;

    [Fact]
    public async Task GetAll_ReturnsEmptyList_WhenNoApplicationsExist()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var response = await _client.GetAsync("/api/applications");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var items = await response.Content.ReadFromJsonAsync<List<JobApplication>>(JsonOpts);
        Assert.Empty(items!);
    }

    [Fact]
    public async Task Post_CreatesApplication_AndReturns201()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var dto = new { Company = "Acme", Role = "Engineer" };

        var response = await _client.PostAsJsonAsync("/api/applications", dto);

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var created = await response.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);
        Assert.Equal("Acme", created!.Company);
    }

    [Fact]
    public async Task UserA_CannotAccess_UserB_Application()
    {
        // User 1 creates an application
        TestCurrentUserService.CurrentUserId = 1;
        var createResponse = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Secret Corp", Role = "Admin" });
        var created = await createResponse.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);

        // User 2 tries to access it — must get 404, not 403
        TestCurrentUserService.CurrentUserId = 2;
        var response = await _client.GetAsync($"/api/applications/{created!.Id}");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task GetAll_OnlyReturnsCurrentUserApplications()
    {
        // User 1 creates an application
        TestCurrentUserService.CurrentUserId = 1;
        await _client.PostAsJsonAsync("/api/applications", new { Company = "Alpha", Role = "Dev" });

        // User 2 creates a different application
        TestCurrentUserService.CurrentUserId = 2;
        await _client.PostAsJsonAsync("/api/applications", new { Company = "Beta", Role = "Lead" });

        // User 1 lists applications — should only see their own
        TestCurrentUserService.CurrentUserId = 1;
        var response = await _client.GetAsync("/api/applications");
        var items = await response.Content.ReadFromJsonAsync<List<JobApplication>>(JsonOpts);

        Assert.Single(items!);
        Assert.Equal("Alpha", items![0].Company);
    }

    [Fact]
    public async Task Post_Note_CreatesNote_AndReturns201()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var createApp = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Acme", Role = "Dev" });
        var app = await createApp.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);

        var response = await _client.PostAsJsonAsync(
            $"/api/applications/{app!.Id}/notes", new { Content = "Great culture fit." });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }

    [Fact]
    public async Task Get_Notes_ReturnsNotFound_ForAnotherUsersApplication()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var createApp = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Secret Corp", Role = "Dev" });
        var app = await createApp.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);

        TestCurrentUserService.CurrentUserId = 2;
        var response = await _client.GetAsync($"/api/applications/{app!.Id}/notes");

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Patch_Status_RecordsTransitionHistory()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var createResponse = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Initech", Role = "Dev" });
        var app = await createResponse.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);

        var response = await _client.PatchAsJsonAsync(
            $"/api/applications/{app!.Id}/status",
            new { NewStatus = (int)ApplicationStatus.Screening });

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var updated = await response.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);
        Assert.Equal(ApplicationStatus.Screening, updated!.Status);
    }

    [Fact]
    public async Task Post_SerializesStatus_AsString_NotInteger()
    {
        // Regression: enums serialized as ints (status:0) leave the kanban board
        // empty because the client filters by string status ("Applied").
        TestCurrentUserService.CurrentUserId = 1;
        var response = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Acme", Role = "Dev" });

        using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
        var status = doc.RootElement.GetProperty("status");
        Assert.Equal(JsonValueKind.String, status.ValueKind);
        Assert.Equal("Applied", status.GetString());
    }

    [Fact]
    public async Task Patch_Status_BlocksTransition_FromTerminalState()
    {
        TestCurrentUserService.CurrentUserId = 1;
        var createResponse = await _client.PostAsJsonAsync("/api/applications",
            new { Company = "Initech", Role = "Dev" });
        var app = await createResponse.Content.ReadFromJsonAsync<JobApplication>(JsonOpts);

        // First transition to Rejected
        await _client.PatchAsJsonAsync($"/api/applications/{app!.Id}/status",
            new { NewStatus = (int)ApplicationStatus.Rejected });

        // Attempt to transition out of Rejected — must fail
        var response = await _client.PatchAsJsonAsync($"/api/applications/{app.Id}/status",
            new { NewStatus = (int)ApplicationStatus.Screening });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }
}