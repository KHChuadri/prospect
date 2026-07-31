using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using JobApplicationTracker.Services;
using JobApplicationTracker.Models;
using JobApplicationTracker.DTOs.Applications;
using JobApplicationTracker.DTOs.Status;

namespace JobApplicationTracker.Controllers;

[Authorize]
[ApiController]
[Route("api/applications")]
public class ApplicationsController : ControllerBase
{
    private readonly IApplicationService _applications;
    private readonly ICurrentUserService _currentUser;

    public ApplicationsController(IApplicationService applications, ICurrentUserService currentUser)
    {
        _applications = applications;
        _currentUser = currentUser;
    }

    [HttpGet]
    [ProducesResponseType(typeof(List<JobApplication>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll([FromQuery] ApplicationStatus? status) =>
        Ok(await _applications.GetAllAsync(_currentUser.UserId, status));

    [HttpGet("{id}")]
    [ProducesResponseType(typeof(JobApplication), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(int id)
    {
        var app = await _applications.GetByIdAsync(_currentUser.UserId, id);
        return app is null ? NotFound() : Ok(app);
    }

    [HttpPost]
    [ProducesResponseType(typeof(JobApplication), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Create([FromBody] CreateApplicationDto dto)
    {
        var app = await _applications.CreateAsync(_currentUser.UserId, dto);
        return CreatedAtAction(nameof(GetById), new { id = app.Id }, app);
    }

    [HttpPatch("{id}")]
    [ProducesResponseType(typeof(JobApplication), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Update(int id, [FromBody] UpdateApplicationDto dto)
    {
        var app = await _applications.UpdateAsync(_currentUser.UserId, id, dto);
        return app is null ? NotFound() : Ok(app);
    }

    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Delete(int id)
    {
        var deleted = await _applications.DeleteAsync(_currentUser.UserId, id);
        return deleted ? NoContent() : NotFound();
    }

    [HttpPatch("{id}/status")]
    [ProducesResponseType(typeof(JobApplication), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateStatus(int id, [FromBody] UpdateStatusDto dto)
    {
        var result = await _applications.UpdateStatusAsync(_currentUser.UserId, id, dto);

        return result switch
        {
            { NotFound: true } => NotFound(),
            { Error: not null } => BadRequest(new { message = result.Error }),
            _ => Ok(result.Value)
        };
    }
}
