using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using JobApplicationTracker.DTOs.Users;
using JobApplicationTracker.Services;

namespace JobApplicationTracker.Controllers;

[Authorize]
[ApiController]
[Route("api/users")]
public class UsersController : ControllerBase
{
    private readonly IUsersService _users;
    private readonly ICurrentUserService _currentUser;

    public UsersController(IUsersService users, ICurrentUserService currentUser)
    {
        _users = users;
        _currentUser = currentUser;
    }

    [HttpGet("me")]
    [ProducesResponseType(typeof(MeDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetMe()
    {
        var me = await _users.GetAsync(_currentUser.UserId);
        return me is null ? NotFound() : Ok(me);
    }

    [HttpPut("me")]
    [ProducesResponseType(typeof(MeDto), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> UpdateMe([FromBody] UpdateMeDto dto)
    {
        var me = await _users.UpdateAsync(_currentUser.UserId, dto);
        return me is null ? NotFound() : Ok(me);
    }
}
