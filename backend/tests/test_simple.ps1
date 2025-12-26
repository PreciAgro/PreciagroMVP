# Simple test script for temporal endpoints
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
$eventId = "test_event_$(Get-Random)"
$taskId = "test_task_$(Get-Random)"

# Test event data
$eventJson = @"
{
    "topic": "weather.forecast",
    "id": "$eventId", 
    "ts_utc": "$timestamp",
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
    "task_id": "$taskId",
    "user_id": "user_123",
    "outcome": "done",
    "timestamp": "$timestamp",
    "metadata": {
        "notes": "Completed successfully"
    }
}
"@

Write-Host "Testing Temporal Logic Endpoints"
Write-Host "=================================="

# Test 1: Health
Write-Host "`nTesting Health Endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/health" -Method GET
    Write-Host "SUCCESS - Status: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
} catch {
    Write-Host "FAILED - Health: $($_.Exception.Message)"
}

# Test 2: Intents
Write-Host "`nTesting Intents Endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/intents" -Method GET
    Write-Host "SUCCESS - Status: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
} catch {
    Write-Host "FAILED - Intents: $($_.Exception.Message)"
}

# Test 3: Event Ingestion
Write-Host "`nTesting Event Ingestion..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/events" -Method POST -Body $eventJson -ContentType "application/json"
    Write-Host "SUCCESS - Status: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
} catch {
    Write-Host "FAILED - Event ingestion: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        Write-Host "Error details: $($_.ErrorDetails.Message)"
    }
}

# Test 4: Get Schedule
Write-Host "`nTesting Get Schedule..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/schedule/user_123" -Method GET
    Write-Host "SUCCESS - Status: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
} catch {
    Write-Host "FAILED - Get schedule: $($_.Exception.Message)"
}

# Test 5: Record Outcome
Write-Host "`nTesting Record Outcome..."
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/outcomes" -Method POST -Body $outcomeJson -ContentType "application/json"
    Write-Host "SUCCESS - Status: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
} catch {
    Write-Host "FAILED - Record outcome: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        Write-Host "Error details: $($_.ErrorDetails.Message)"
    }
}

Write-Host "`nTesting Complete!"
