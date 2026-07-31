using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.Models;

public class StatusTransition
{
  public int Id { get; set; }

  public int ApplicationId { get; set; }
  public JobApplication Application { get; set; } = null!;

  public ApplicationStatus FromStatus { get; set; }
  public ApplicationStatus ToStatus { get; set; }

  public DateTime TransitionedAt { get; set; } = DateTime.UtcNow;
}