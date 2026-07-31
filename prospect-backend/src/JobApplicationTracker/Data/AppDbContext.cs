using JobApplicationTracker.Models;
using JobApplicationTracker.Services;
using Microsoft.EntityFrameworkCore;

namespace JobApplicationTracker.Data;

public class AppDbContext : DbContext
{
  private readonly ICurrentUserService _currentUserService;

  public AppDbContext(DbContextOptions<AppDbContext> options, ICurrentUserService currentUserService) : base(options) 
  {
    _currentUserService = currentUserService;
  }

  public DbSet<User> Users => Set<User>();
  public DbSet<JobApplication> JobApplications => Set<JobApplication>();
  public DbSet<Note> Notes => Set<Note>();
  public DbSet<StatusTransition> StatusTransitions => Set<StatusTransition>();

  protected override void OnModelCreating(ModelBuilder modelBuilder)
  {
    modelBuilder.Entity<JobApplication>()
      .HasQueryFilter(a => a.UserId == _currentUserService.UserId);

    modelBuilder.Entity<StatusTransition>()
      .HasQueryFilter(st => st.Application.UserId == _currentUserService.UserId);

    modelBuilder.Entity<User>()
      .HasIndex(u => u.Email)
      .IsUnique();
  }
}