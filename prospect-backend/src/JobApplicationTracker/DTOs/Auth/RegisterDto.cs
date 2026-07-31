using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.DTOs.Auth;
public class RegisterDto
{
  [Required, EmailAddress, MaxLength(200)]
  public string Email { get; set; } = string.Empty;

  [Required, MinLength(8)]
  public string Password { get; set; } = string.Empty;
}