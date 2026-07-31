using JobApplicationTracker.Data;
using JobApplicationTracker.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace JobApplicationTracker.Controllers;

[Authorize]
[ApiController]
[Route("api/analytics")]
public class AnalyticsController : ControllerBase
{
    private readonly AppDbContext _db;

    public AnalyticsController(AppDbContext db) => _db = db;

    [HttpGet("summary")]
    public async Task<IActionResult> GetSummary()
    {
        var applications = await _db.JobApplications.ToListAsync();

        var countsByStatus = Enum.GetValues<ApplicationStatus>()
            .ToDictionary(
                s => s.ToString(),
                s => applications.Count(a => a.Status == s));

        var perWeek = applications
            .GroupBy(a => ISOWeek(a.AppliedAt))
            .OrderBy(g => g.Key)
            .Select(g => new { week = g.Key, count = g.Count() })
            .ToList();

        var transitions = await _db.StatusTransitions
            .OrderBy(t => t.ApplicationId)
            .ThenBy(t => t.TransitionedAt)
            .ToListAsync();

        // Time in FromStatus = delta between this transition and the previous one for same application
        var avgTimeInStage = transitions
            .GroupBy(t => t.FromStatus)
            .ToDictionary(
                g => g.Key.ToString(),
                g => g.Average(t =>
                    (t.TransitionedAt - (
                        transitions
                            .Where(p => p.ApplicationId == t.ApplicationId && p.TransitionedAt < t.TransitionedAt)
                            .OrderByDescending(p => p.TransitionedAt)
                            .FirstOrDefault()?.TransitionedAt ?? t.TransitionedAt)
                    ).TotalHours));

        return Ok(new
        {
            countsByStatus,
            applicationsPerWeek = perWeek,
            averageHoursInStage = avgTimeInStage
        });
    }

    private static string ISOWeek(DateTime date)
    {
        var week = System.Globalization.ISOWeek.GetWeekOfYear(date);
        return $"{date.Year}-W{week:D2}";
    }
}
