namespace JobApplicationTracker.Services;

public sealed record ServiceResult<T>
{
    public T? Value { get; init; }
    public string? Error { get; init; }
    public bool NotFound { get; init; }

    public bool IsSuccess => !NotFound && Error is null;

    public static ServiceResult<T> Ok(T value) => new() { Value = value };
    public static ServiceResult<T> Fail(string error) => new() { Error = error };
    public static ServiceResult<T> Missing() => new() { NotFound = true };
}
