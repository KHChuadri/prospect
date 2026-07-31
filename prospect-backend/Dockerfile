FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY JobApplicationTracker.slnx .
COPY src/JobApplicationTracker/JobApplicationTracker.csproj src/JobApplicationTracker/
RUN dotnet restore src/JobApplicationTracker/JobApplicationTracker.csproj
COPY . .
RUN dotnet publish src/JobApplicationTracker -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "JobApplicationTracker.dll"]
