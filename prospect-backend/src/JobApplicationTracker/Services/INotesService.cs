using JobApplicationTracker.DTOs.Notes;
using JobApplicationTracker.Models;

namespace JobApplicationTracker.Services;

public interface INotesService
{
    Task<List<Note>?> GetAllForApplicationAsync(int userId, int applicationId);
    Task<Note?> CreateAsync(int userId, int applicationId, CreateNoteDto dto);
}
