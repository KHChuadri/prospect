using JobApplicationTracker.DTOs.Auth;

namespace JobApplicationTracker.Services;

public interface IAuthService
{
    Task<(AuthResponseDto Response, bool EmailTaken)> RegisterAsync(RegisterDto dto);
    Task<AuthResponseDto?> LoginAsync(LoginDto dto);
    Task<AuthResponseDto?> RefreshAsync(string refreshToken);
    Task RevokeAsync(int userId);
}
