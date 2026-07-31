using JobApplicationTracker.DTOs.Applications;
using JobApplicationTracker.DTOs.Status;
using JobApplicationTracker.Models;

namespace JobApplicationTracker.Services;

public interface IApplicationService
{
    Task<List<JobApplication>> GetAllAsync(int userId, ApplicationStatus? status);
    Task<JobApplication?> GetByIdAsync(int userId, int id);
    Task<JobApplication> CreateAsync(int userId, CreateApplicationDto dto);
    Task<JobApplication?> UpdateAsync(int userId, int id, UpdateApplicationDto dto);
    Task<bool> DeleteAsync(int userId, int id);
    Task<ServiceResult<JobApplication>> UpdateStatusAsync(int userId, int id, UpdateStatusDto dto);
}
