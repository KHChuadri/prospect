using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using JobApplicationTracker.Models;
using Microsoft.IdentityModel.Tokens;

namespace JobApplicationTracker.Services;

public class TokenService : ITokenService
{
  private readonly IConfiguration _config;
  
  public TokenService(IConfiguration config) => _config = config;

  public string GenerateAccessToken(User user)
  {
    var key = new SymmetricSecurityKey(
      Encoding.UTF8.GetBytes(_config["JwtSettings:SecretKey"]!)
    );

    var claims = new[]
    {
      new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
      new Claim(ClaimTypes.Email, user.Email)
    };

    var token = new JwtSecurityToken(
      issuer: _config["JwtSettings:Issuer"],
      audience: _config["JwtSettings:Audience"],
      claims: claims,
      expires: DateTime.UtcNow.AddMinutes(
        double.Parse(_config["JwtSettings:ExpiryMinutes"]!)
      ),
       signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256)
    );

    return new JwtSecurityTokenHandler().WriteToken(token);
  }

  public string GenerateRefreshToken()
  {
    var bytes = new byte[64];
    RandomNumberGenerator.Fill(bytes);
    return Convert.ToBase64String(bytes);
  }
}