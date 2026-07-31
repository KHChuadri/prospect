using System.Net.Http.Json;

namespace JobApplicationTracker.Tests.Helpers;

public static class AuthHelper
{
    public static async Task<string> RegisterAndLoginAsync(
        HttpClient client, string email = "test@test.com", string password = "Password123!")
    {
        await client.PostAsJsonAsync("/api/auth/register", new { email, password });

        var loginResponse = await client.PostAsJsonAsync("/api/auth/login", new { email, password });
        var result = await loginResponse.Content.ReadFromJsonAsync<AuthResponse>();
        return result!.AccessToken;
    }

    private record AuthResponse(string AccessToken, string RefreshToken);
}
