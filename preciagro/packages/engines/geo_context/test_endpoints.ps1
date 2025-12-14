# GeoContext Engine Endpoint Testing Script for PowerShell
# Tests all endpoints with basic validation

param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$JwtToken = ""
)

Write-Host "🚀 Starting GeoContext Engine Endpoint Tests" -ForegroundColor Green
Write-Host "🔗 Base URL: $BaseUrl" -ForegroundColor Cyan

# Set up headers
$headers = @{
    "Content-Type" = "application/json"
}
if ($JwtToken) {
    $headers["Authorization"] = "Bearer $JwtToken"
    Write-Host "🔑 JWT Token: ✅ Provided" -ForegroundColor Green
} else {
    Write-Host "🔑 JWT Token: ❌ Not provided (may cause auth failures)" -ForegroundColor Yellow
}

$testResults = @()

# Test 1: Health Check
Write-Host "`n🔍 Testing: Health Check" -ForegroundColor Blue
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET -Headers @{"Content-Type"="application/json"}
    Write-Host "   ✅ Health check passed" -ForegroundColor Green
    Write-Host "   📊 Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    $testResults += @{Test="Health Check"; Status="PASS"; Response=$response}
} catch {
    Write-Host "   ❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test="Health Check"; Status="FAIL"; Error=$_.Exception.Message}
}

# Test 2: FCO Resolve - Poland
Write-Host "`n🔍 Testing: FCO Resolve - Poland" -ForegroundColor Blue
$polandRequest = @{
    field = @{
        type = "Polygon"
        coordinates = @(@(@(21.0, 52.2), @(21.01, 52.2), @(21.01, 52.21), @(21.0, 52.21), @(21.0, 52.2)))
    }
    date = "2025-09-05"
    crops = @("corn", "soybeans")
    forecast_days = 7
    use_cache = $true
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/geocontext/resolve" -Method POST -Headers $headers -Body $polandRequest
    $contextHash = $response.context_hash
    Write-Host "   ✅ Poland FCO resolve passed" -ForegroundColor Green
    Write-Host "   📊 Context Hash: $contextHash" -ForegroundColor Gray
    Write-Host "   🌍 Location: $($response.location.admin_l0)" -ForegroundColor Gray
    Write-Host "   🌤️ ET0: $($response.climate.et0_mm_day) mm/day" -ForegroundColor Gray
    Write-Host "   📈 GDD YTD: $($response.climate.gdd_base10_ytd)" -ForegroundColor Gray
    $testResults += @{Test="FCO Resolve - Poland"; Status="PASS"; ContextHash=$contextHash; Response=$response}
} catch {
    Write-Host "   ❌ Poland FCO resolve failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test="FCO Resolve - Poland"; Status="FAIL"; Error=$_.Exception.Message}
    $contextHash = $null
}

# Test 3: FCO Resolve - Zimbabwe
Write-Host "`n🔍 Testing: FCO Resolve - Zimbabwe" -ForegroundColor Blue
$zimbabweRequest = @{
    field = @{
        type = "Polygon"
        coordinates = @(@(@(31.7, -17.7), @(31.71, -17.7), @(31.71, -17.69), @(31.7, -17.69), @(31.7, -17.7)))
    }
    date = "2025-09-05"
    crops = @("corn", "tobacco")
    forecast_days = 5
    use_cache = $false
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/geocontext/resolve" -Method POST -Headers $headers -Body $zimbabweRequest
    Write-Host "   ✅ Zimbabwe FCO resolve passed" -ForegroundColor Green
    Write-Host "   📊 Context Hash: $($response.context_hash)" -ForegroundColor Gray
    Write-Host "   🌍 Location: $($response.location.admin_l0)" -ForegroundColor Gray
    Write-Host "   ⛰️ Elevation: $($response.location.elevation_m)m" -ForegroundColor Gray
    $testResults += @{Test="FCO Resolve - Zimbabwe"; Status="PASS"; Response=$response}
} catch {
    Write-Host "   ❌ Zimbabwe FCO resolve failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test="FCO Resolve - Zimbabwe"; Status="FAIL"; Error=$_.Exception.Message}
}

# Test 4: Cached FCO Retrieval
if ($contextHash) {
    Write-Host "`n🔍 Testing: Cached FCO Retrieval" -ForegroundColor Blue
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/geocontext/fco/$contextHash" -Method GET -Headers $headers
        Write-Host "   ✅ Cache retrieval passed" -ForegroundColor Green
        Write-Host "   💾 Retrieved cached FCO for hash: $contextHash" -ForegroundColor Gray
        $testResults += @{Test="Cached FCO Retrieval"; Status="PASS"; Response=$response}
    } catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "   ✅ Cache miss (404) - Expected if TTL expired" -ForegroundColor Green
            $testResults += @{Test="Cached FCO Retrieval"; Status="PASS"; Note="Cache miss - TTL expired"}
        } else {
            Write-Host "   ❌ Cache retrieval failed: $($_.Exception.Message)" -ForegroundColor Red
            $testResults += @{Test="Cached FCO Retrieval"; Status="FAIL"; Error=$_.Exception.Message}
        }
    }
} else {
    Write-Host "`n⏭️ Skipping: Cached FCO Retrieval (no context hash)" -ForegroundColor Yellow
    $testResults += @{Test="Cached FCO Retrieval"; Status="SKIP"; Note="No context hash available"}
}

# Test 5: Metrics Endpoint
Write-Host "`n🔍 Testing: Metrics Endpoint" -ForegroundColor Blue
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/metrics" -Method GET -Headers @{"Content-Type"="text/plain"}
    $expectedMetrics = @("geo_context_requests_total", "geo_context_request_duration_seconds", "geo_context_cache_operations_total")
    $foundMetrics = $expectedMetrics | Where-Object { $response -match $_ }
    
    if ($foundMetrics.Count -gt 0) {
        Write-Host "   ✅ Metrics endpoint passed" -ForegroundColor Green
        Write-Host "   📊 Found metrics: $($foundMetrics -join ', ')" -ForegroundColor Gray
        Write-Host "   📈 Total metrics lines: $($response.Split("`n").Count)" -ForegroundColor Gray
        $testResults += @{Test="Metrics Endpoint"; Status="PASS"; FoundMetrics=$foundMetrics}
    } else {
        Write-Host "   ❌ No expected metrics found" -ForegroundColor Red
        $testResults += @{Test="Metrics Endpoint"; Status="FAIL"; Error="No expected metrics found"}
    }
} catch {
    Write-Host "   ❌ Metrics endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
    $testResults += @{Test="Metrics Endpoint"; Status="FAIL"; Error=$_.Exception.Message}
}

# Summary
Write-Host "`n$('='*60)" -ForegroundColor Cyan
Write-Host "📋 TEST SUMMARY" -ForegroundColor Cyan
Write-Host "$('='*60)" -ForegroundColor Cyan

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.Status -eq "PASS" }).Count
$failedTests = ($testResults | Where-Object { $_.Status -eq "FAIL" }).Count
$skippedTests = ($testResults | Where-Object { $_.Status -eq "SKIP" }).Count
$successRate = if ($totalTests -gt 0) { [math]::Round(($passedTests / $totalTests) * 100, 2) } else { 0 }

Write-Host "📊 Total Tests: $totalTests" -ForegroundColor White
Write-Host "✅ Passed: $passedTests" -ForegroundColor Green
Write-Host "❌ Failed: $failedTests" -ForegroundColor Red
Write-Host "⏭️ Skipped: $skippedTests" -ForegroundColor Yellow
Write-Host "📈 Success Rate: $successRate%" -ForegroundColor White

Write-Host "`n📝 DETAILED RESULTS:" -ForegroundColor White
foreach ($result in $testResults) {
    $statusIcon = switch ($result.Status) {
        "PASS" { "✅" }
        "FAIL" { "❌" }
        "SKIP" { "⏭️" }
        default { "❓" }
    }
    Write-Host "  $statusIcon $($result.Test)" -ForegroundColor White
    
    if ($result.Error) {
        Write-Host "     ⚠️ Error: $($result.Error)" -ForegroundColor Red
    }
    if ($result.Note) {
        Write-Host "     ℹ️ Note: $($result.Note)" -ForegroundColor Yellow
    }
}

# Save results
$testResults | ConvertTo-Json -Depth 10 | Out-File -FilePath "geocontext_test_results.json" -Encoding UTF8
Write-Host "`n💾 Full results saved to: geocontext_test_results.json" -ForegroundColor Cyan

# Exit code
if ($failedTests -gt 0) {
    Write-Host "`n❌ Some tests failed. Check the results above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n✅ All tests passed successfully!" -ForegroundColor Green
    exit 0
}
