using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using JobApplicationTracker.DTOs.Notes;
using JobApplicationTracker.Models;
using JobApplicationTracker.Services;

namespace JobApplicationTracker.Controllers;

[Authorize]
[ApiController]
[Route("api/applications/{applicationId}/notes")]
public class NotesController : ControllerBase
{
    private readonly INotesService _notes;
    private readonly ICurrentUserService _currentUser;

    public NotesController(INotesService notes, ICurrentUserService currentUser)
    {
        _notes = notes;
        _currentUser = currentUser;
    }

    [HttpGet]
    [ProducesResponseType(typeof(List<Note>), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetAll(int applicationId)
    {
        var notes = await _notes.GetAllForApplicationAsync(_currentUser.UserId, applicationId);
        return notes is null ? NotFound() : Ok(notes);
    }

    [HttpPost]
    [ProducesResponseType(typeof(Note), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Create(int applicationId, [FromBody] CreateNoteDto dto)
    {
        var note = await _notes.CreateAsync(_currentUser.UserId, applicationId, dto);
        return note is null
            ? NotFound()
            : CreatedAtAction(nameof(GetAll), new { applicationId }, note);
    }
}
