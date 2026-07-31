using JobApplicationTracker.Data;
using JobApplicationTracker.DTOs.Applications;
using JobApplicationTracker.DTOs.Status;
using JobApplicationTracker.Models;
using Microsoft.EntityFrameworkCore;

namespace JobApplicationTracker.Services;

public class ApplicationService : IApplicationService
{
    private readonly AppDbContext _db;

    public ApplicationService(AppDbContext db) => _db = db;

    public async Task<List<JobApplication>> GetAllAsync(int userId, ApplicationStatus? status)
    {
        var query = _db.JobApplications.AsQueryable();

        if (status.HasValue)
            query = query.Where(a => a.Status == status.Value);

        return await query.ToListAsync();
    }

    public async Task<JobApplication?> GetByIdAsync(int userId, int id) =>
        await _db.JobApplications.FindAsync(id);

    public async Task<JobApplication> CreateAsync(int userId, CreateApplicationDto dto)
    {
        var app = new JobApplication
        {
            UserId = userId,
            Company = dto.Company,
            Role = dto.Role,
            Source = dto.Source,
            SalaryRange = dto.SalaryRange
        };

        _db.JobApplications.Add(app);
        await _db.SaveChangesAsync();
        return app;
    }

    public async Task<JobApplication?> UpdateAsync(int userId, int id, UpdateApplicationDto dto)
    {
        var app = await _db.JobApplications.FindAsync(id);
        if (app is null) return null;

        if (dto.Company is not null) app.Company = dto.Company;
        if (dto.Role is not null) app.Role = dto.Role;
        if (dto.Source is not null) app.Source = dto.Source;
        if (dto.SalaryRange is not null) app.SalaryRange = dto.SalaryRange;

        await _db.SaveChangesAsync();
        return app;
    }

    public async Task<bool> DeleteAsync(int userId, int id)
    {
        var app = await _db.JobApplications.FindAsync(id);
        if (app is null) return false;

        _db.JobApplications.Remove(app);
        await _db.SaveChangesAsync();
        return true;
    }

    public async Task<ServiceResult<JobApplication>> UpdateStatusAsync(int userId, int id, UpdateStatusDto dto)
    {
        var app = await _db.JobApplications.FindAsync(id);
        if (app is null) return ServiceResult<JobApplication>.Missing();

        var terminalStates = new[] { ApplicationStatus.Rejected, ApplicationStatus.Withdrawn };
        if (terminalStates.Contains(app.Status))
            return ServiceResult<JobApplication>.Fail($"Cannot transition from terminal status {app.Status}.");

        _db.StatusTransitions.Add(new StatusTransition
        {
            ApplicationId = app.Id,
            FromStatus = app.Status,
            ToStatus = dto.NewStatus,
        });

        app.Status = dto.NewStatus;
        await _db.SaveChangesAsync();

        return ServiceResult<JobApplication>.Ok(app);
    }
}
