using System.ComponentModel.DataAnnotations;
using JobApplicationTracker.Models;

namespace JobApplicationTracker.DTOs.Status;

public class UpdateStatusDto
{
  [Required]
  public ApplicationStatus NewStatus { get; set; }
}