using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.Models;

public class Note
{
  public int Id { get; set; }
  public int ApplicationId { get; set; }
  public JobApplication Application = null!;

  [Required]
  public string Content { get; set; } = string.Empty;

  public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}