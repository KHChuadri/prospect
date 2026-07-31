using System.Security.Claims;

namespace JobApplicationTracker.Services;

public class CurrentUserService : ICurrentUserService
{
  public int UserId { get; }

  public CurrentUserService(IHttpContextAccessor httpContextAccessor)
  {
    var value = httpContextAccessor.HttpContext?.User?.FindFirstValue(ClaimTypes.NameIdentifier);
    UserId = int.TryParse(value, out var id) ? id : 0;
  }
}