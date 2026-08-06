using JobApplicationTracker.DTOs.Users;

namespace JobApplicationTracker.Services;

public interface IUsersService
{
  Task<MeDto?> GetAsync(int userId);
  Task<MeDto?> UpdateAsync(int userId, UpdateMeDto dto);
}
