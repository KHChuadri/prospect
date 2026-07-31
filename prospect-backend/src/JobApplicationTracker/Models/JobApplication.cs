using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.Models;

public class JobApplication
{
  public int Id { get; set; }

  public int UserId { get; set; }

  public User User { get; set; } = null!;

  [Required, MaxLength(200)]
  public string Company { get; set; } = string.Empty;

  [Required, MaxLength(200)]
  public string Role { get; set; } = string.Empty;

  public ApplicationStatus Status { get; set; } = ApplicationStatus.Applied;

  [MaxLength(100)]
  public string? Source { get; set; }

  public string? SalaryRange { get; set; }

  public DateTime AppliedAt { get; set; } = DateTime.UtcNow;

  public ICollection<Note> Notes { get; set; } = [];

  public ICollection<StatusTransition> StatusTransitions { get; set; } = [];
}