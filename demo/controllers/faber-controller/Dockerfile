FROM mcr.microsoft.com/dotnet/core/sdk:3.1 as build
WORKDIR /app

# Copy csproj and restore distinct layers
COPY *.sln .
COPY FaberController/*.csproj ./FaberController/
RUN dotnet restore

# Copy and build app
COPY FaberController/. ./FaberController/
WORKDIR /app/FaberController
RUN dotnet publish -c Release -o out

FROM mcr.microsoft.com/dotnet/core/aspnet:3.1 as runtime
WORKDIR /app
COPY --from=build /app/FaberController/out ./
ENTRYPOINT ["dotnet", "FaberController.dll"]