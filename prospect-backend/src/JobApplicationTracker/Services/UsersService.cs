using JobApplicationTracker.Data;
using JobApplicationTracker.DTOs.Users;

namespace JobApplicationTracker.Services;

public class UsersService : IUsersService
{
  private readonly AppDbContext _db;

  public UsersService(AppDbContext db) => _db = db;

  public async Task<MeDto?> GetAsync(int userId)
  {
    var user = await _db.Users.FindAsync(userId);
    return user is null ? null : new MeDto { Email = user.Email, City = user.City };
  }

  public async Task<MeDto?> UpdateAsync(int userId, UpdateMeDto dto)
  {
    var user = await _db.Users.FindAsync(userId);
    if (user is null) return null;
    // Trimmed to empty is the same intent as unset — the agent treats both
    // as "no city" and skips the filter.
    var city = dto.City?.Trim();
    user.City = string.IsNullOrEmpty(city) ? null : city;
    await _db.SaveChangesAsync();
    return new MeDto { Email = user.Email, City = user.City };
  }
}
