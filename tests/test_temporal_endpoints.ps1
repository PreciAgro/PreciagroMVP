"""Quick PowerShell test script for temporal endpoints."""

# Test event data
$eventJson = @"
{
    "topic": "weather.forecast",
    "id": "test_event_001", 
    "ts_utc": "2025-08-29T07:35:00.000Z",
    "farm_id": "farm_123",
    "farmer_tz": "America/New_York",
    "payload": {
        "temperature": 35,
        "humidity": 85,
        "crop_type": "tomato"
    }
}
"@

# Test outcome data
$outcomeJson = @"
{
    "task_id": "test_task_001",
    "user_id": "user_123",
    "outcome": "done",
    "timestamp": "2025-08-29T08:59:00.000Z",
    "metadata": {
        "notes": "Completed successfully"
    }
}
"@

Write-Host "🚀 Testing Temporal Logic Endpoints" -ForegroundColor Green
Write-Host "=" * 50

# Test 1: Health Check
Write-Host "`n🏥 Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/health" -Method GET
    Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Intents
Write-Host "`n🎯 Testing Intents Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/intents" -Method GET
    Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Intents test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Ingest Event
Write-Host "`n📥 Testing Event Ingestion..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/events" -Method POST -Body $eventJson -ContentType "application/json"
    Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Event ingestion failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Error details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# Test 4: Get Schedule
Write-Host "`n📅 Testing Get Schedule..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/schedule/user_123" -Method GET
    Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Get schedule failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Error details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# Test 5: Record Outcome
Write-Host "`n✅ Testing Record Outcome..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/outcomes" -Method POST -Body $outcomeJson -ContentType "application/json"
    Write-Host "✅ Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Record outcome failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Error details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}

Write-Host "`n🏁 Testing Complete!" -ForegroundColor Green
