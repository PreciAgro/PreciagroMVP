# Run Crop Intelligence Engine (CIE)
# Usage: .\run_cie.ps1

Write-Host "🌱 Starting Crop Intelligence Engine..." -ForegroundColor Green

# Check if we're in the right directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootPath = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptPath)))

Set-Location $rootPath

Write-Host "Working directory: $rootPath" -ForegroundColor Cyan

# Run the service
Write-Host "`nStarting FastAPI service on http://localhost:8082" -ForegroundColor Yellow
Write-Host "API Documentation: http://localhost:8082/docs" -ForegroundColor Yellow
Write-Host "`nPress Ctrl+C to stop the service`n" -ForegroundColor Gray

uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082
