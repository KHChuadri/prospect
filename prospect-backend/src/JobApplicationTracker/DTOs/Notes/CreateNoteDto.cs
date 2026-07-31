using System.ComponentModel.DataAnnotations;

namespace JobApplicationTracker.DTOs.Notes;

public class CreateNoteDto
{
  [Required]
  public string? Content { get; set; }
}