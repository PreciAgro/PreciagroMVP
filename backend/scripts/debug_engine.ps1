# Debug the real temporal logic engine
Write-Host "=== DEBUGGING TEMPORAL LOGIC ENGINE ===" -ForegroundColor Yellow

# Test with a weather event that should match our spray rule
Write-Host "`n🌡️ Testing Weather Event Debug..."
$weatherEvent = @{
    "event" = @{
        "topic" = "weather.forecast"
        "id" = "debug_weather_001"
        "ts_utc" = "2025-09-03T10:00:00.000Z"
        "farm_id" = "farm_tomato_123"
        "farmer_tz" = "America/New_York"
        "payload" = @{
            "temperature" = 35
            "humidity" = 45
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "Sending event:" -ForegroundColor Cyan
Write-Host $weatherEvent -ForegroundColor Gray

try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/events" -Method POST -Body $weatherEvent -ContentType "application/json"
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "✅ Response Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "📊 Tasks Created: $($result.tasks_created)" -ForegroundColor $(if($result.tasks_created -gt 0) { "Green" } else { "Red" })
    Write-Host "🆔 Task IDs: $($result.task_ids -join ', ')" -ForegroundColor Cyan
    
    if ($result.tasks_created -gt 0) {
        Write-Host "`n🎯 SUCCESS: Rule triggered and task created!" -ForegroundColor Green
        
        # Now check the schedule to see our task
        Write-Host "`n📅 Checking farmer schedule..."
        $schedule = Invoke-WebRequest -Uri "http://127.0.0.1:8000/temporal/schedule/farmer_farm_tomato_123" -Method GET
        $scheduleData = $schedule.Content | ConvertFrom-Json
        
        Write-Host "📋 Scheduled Tasks: $($scheduleData.schedule.Count)" -ForegroundColor Cyan
        foreach ($task in $scheduleData.schedule) {
            Write-Host "  📝 Task: $($task.message)" -ForegroundColor White
            Write-Host "  ⏰ When: $($task.schedule_time)" -ForegroundColor White
            Write-Host "  🎯 Priority: $($task.priority)" -ForegroundColor White
            Write-Host "  📱 Channels: $($task.channels -join ', ')" -ForegroundColor White
            Write-Host ""
        }
    } else {
        Write-Host "`n❌ NO TASKS CREATED - Need to debug rule matching!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

Write-Host "`n=== DEBUG COMPLETE ===" -ForegroundColor Yellow
