using JobApplicationTracker.Data;
using JobApplicationTracker.DTOs.Notes;
using JobApplicationTracker.Models;
using Microsoft.EntityFrameworkCore;

namespace JobApplicationTracker.Services;

public class NotesService : INotesService
{
    private readonly AppDbContext _db;

    public NotesService(AppDbContext db) => _db = db;

    public async Task<List<Note>?> GetAllForApplicationAsync(int userId, int applicationId)
    {
        var app = await _db.JobApplications
            .Include(a => a.Notes)
            .FirstOrDefaultAsync(a => a.Id == applicationId);

        return app is null ? null : app.Notes.ToList();
    }

    public async Task<Note?> CreateAsync(int userId, int applicationId, CreateNoteDto dto)
    {
        var app = await _db.JobApplications.FindAsync(applicationId);
        if (app is null) return null;

        var note = new Note
        {
            ApplicationId = applicationId,
            Content = dto.Content
        };

        _db.Notes.Add(note);
        await _db.SaveChangesAsync();
        return note;
    }
}
