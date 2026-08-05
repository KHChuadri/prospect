using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.DTOs.Users;

public class UpdateMeDto
{
  [MaxLength(100)]
  public string? City { get; set; }
}
