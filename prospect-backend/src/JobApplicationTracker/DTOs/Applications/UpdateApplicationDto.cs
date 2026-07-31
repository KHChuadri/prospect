using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.DTOs.Applications;

public class UpdateApplicationDto
{
  public string? Company { get; set; }
  public string? Role { get; set; }
  public string? Source { get; set; }
  public string? SalaryRange { get; set; }
}