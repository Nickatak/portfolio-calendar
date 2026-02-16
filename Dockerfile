FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet restore ./Portfolio.Calendar.Api.csproj
RUN dotnet publish ./Portfolio.Calendar.Api.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_URLS=http://0.0.0.0:8002
EXPOSE 8002
ENTRYPOINT ["dotnet", "Portfolio.Calendar.Api.dll"]
