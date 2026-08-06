using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace JobApplicationTracker.Data.Migrations
{
    /// <inheritdoc />
    public partial class AddResumeFileColumns : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "file_key",
                table: "resumes",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "file_name",
                table: "resumes",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "parsed_json",
                table: "resumes",
                type: "jsonb",
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "file_key",
                table: "resumes");

            migrationBuilder.DropColumn(
                name: "file_name",
                table: "resumes");

            migrationBuilder.DropColumn(
                name: "parsed_json",
                table: "resumes");
        }
    }
}
