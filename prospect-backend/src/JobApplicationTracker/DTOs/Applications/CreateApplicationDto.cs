using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.DTOs.Applications;

public class CreateApplicationDto
{
  [Required, MaxLength(200)]
  public string Company { get; set; } = string.Empty;

  [Required, MaxLength(200)]
  public string Role { get; set; } = string.Empty;

  [MaxLength(100)]
  public string? Source { get; set; }

  public string? SalaryRange { get; set; }
}