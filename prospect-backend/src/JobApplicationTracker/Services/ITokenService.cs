using JobApplicationTracker.Models;

namespace JobApplicationTracker.Services;

public interface ITokenService
{
  string GenerateAccessToken(User user);
  string GenerateRefreshToken();
}