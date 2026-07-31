using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.Models;

public class User
{
  public int Id { get; set; }
  
  [Required, MaxLength(200)]
  public string Email { get; set; } = string.Empty;

  [Required]
  public string PasswordHash { get; set; } = string.Empty;

  public string? RefreshToken { get; set; }
  public DateTime? RefreshTokenExpiry { get; set; }
  public ICollection<JobApplication> Applications { get; set; } = [];
}