# CIE Pilot UAT Script - End-to-End Field Workflow Test
# Simulates complete field lifecycle: register → telemetry → actions → feedback
# Usage: .\test_cie_pilot_uat.ps1 -BaseUrl "http://localhost:8082" -FieldId "zw_maize_001"

param(
    [string]$BaseUrl = "http://localhost:8082",
    [string]$FieldId = "zw_maize_001_uat",
    [string]$OutputDir = ".\uat_results"
)

$ErrorActionPreference = "Stop"

# Create output directory
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $OutputDir "uat_log_$timestamp.txt"

function Log-Message {
    param([string]$Message, [string]$Type = "INFO")
    $timestampedMsg = "[$(Get-Date -Format 'HH:mm:ss')] [$Type] $Message"
    Write-Host $timestampedMsg
    Add-Content -Path $logFile -Value $timestampedMsg
}

function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Url,
        [string]$Body = $null,
        [string]$Description
    )
    
    Log-Message "Testing: $Description" "TEST"
    Log-Message "  Method: $Method | URL: $Url"
    
    try {
        $headers = @{
            "Content-Type" = "application/json"
        }
        
        $params = @{
            Uri = $Url
            Method = $Method
            Headers = $headers
        }
        
        if ($Body) {
            $params.Body = $Body
            Log-Message "  Request Body: $Body"
        }
        
        $response = Invoke-RestMethod @params
        $responseJson = $response | ConvertTo-Json -Depth 10
        
        Log-Message "  ✓ SUCCESS" "PASS"
        Log-Message "  Response: $responseJson"
        
        # Save response to file
        $safeName = $Description -replace '[^a-zA-Z0-9_]', '_'
        $responseFile = Join-Path $OutputDir "${timestamp}_${safeName}.json"
        $responseJson | Out-File -FilePath $responseFile
        
        return $response
    }
    catch {
        Log-Message "  ✗ FAILED: $($_.Exception.Message)" "FAIL"
        throw
    }
}

# ==========================
# Test Sequence
# ==========================

Log-Message "========================================" "INFO"
Log-Message "CIE Pilot UAT - Field Lifecycle Test" "INFO"
Log-Message "Field ID: $FieldId" "INFO"
Log-Message "Base URL: $BaseUrl" "INFO"
Log-Message "========================================" "INFO"

# Step 1: Register Field
Log-Message "`n=== STEP 1: Register Field ===" "INFO"

$registerPayload = @{
    field_id = $FieldId
    boundary_geojson = @{
        type = "Polygon"
        coordinates = @(
            @(
                @(30.1234, -17.8234),
                @(30.1254, -17.8234),
                @(30.1254, -17.8254),
                @(30.1234, -17.8254),
                @(30.1234, -17.8234)
            )
        )
    }
    crop = "maize"
    planting_date = "2025-11-10"
    irrigation_access = "none"
    target_yield_band = "2-4 t/ha"
    budget_class = "low"
    region = "zimbabwe_natural_region_ii"
} | ConvertTo-Json -Depth 10

$registerResponse = Test-Endpoint -Method "POST" `
    -Url "$BaseUrl/cie/field/register" `
    -Body $registerPayload `
    -Description "Register_Field"

Start-Sleep -Seconds 2

# Step 2: Post Soil Baseline
Log-Message "`n=== STEP 2: Post Initial Telemetry (Soil + VI + Weather) ===" "INFO"

$telemetryPayload = @{
    field_id = $FieldId
    soil = @{
        src = "soilgrids"
        texture = "loam"
        whc_mm = 140
        uncertainty = "±15%"
        ph = 6.2
        organic_matter_pct = 2.1
    }
    vi = @(
        @{
            date = "2025-12-01"
            ndvi = 0.30
            quality = "good"
            source = "sentinel2"
        },
        @{
            date = "2025-12-08"
            ndvi = 0.34
            quality = "good"
            source = "sentinel2"
        },
        @{
            date = "2025-12-15"
            ndvi = 0.40
            quality = "fair"
            source = "sentinel2"
        },
        @{
            date = "2025-12-22"
            ndvi = 0.48
            quality = "good"
            source = "sentinel2"
        }
    )
    weather = @(
        @{
            ts = "2025-12-20T00:00:00Z"
            tmax = 30
            tmin = 18
            rh = 70
            rain = 12
            wind_ms = 2.5
        },
        @{
            ts = "2025-12-21T00:00:00Z"
            tmax = 31
            tmin = 19
            rh = 68
            rain = 0
            wind_ms = 3.0
        },
        @{
            ts = "2025-12-22T00:00:00Z"
            tmax = 29
            tmin = 17
            rh = 75
            rain = 8
            wind_ms = 2.0
        }
    )
} | ConvertTo-Json -Depth 10

$telemetryResponse = Test-Endpoint -Method "POST" `
    -Url "$BaseUrl/cie/field/telemetry" `
    -Body $telemetryPayload `
    -Description "Post_Telemetry"

Start-Sleep -Seconds 2

# Step 3: Get Actions
Log-Message "`n=== STEP 3: Get Action Recommendations ===" "INFO"

$actionsResponse = Test-Endpoint -Method "GET" `
    -Url "$BaseUrl/cie/field/actions?field_id=$FieldId" `
    -Description "Get_Actions"

Start-Sleep -Seconds 1

# Step 4: Simulate User Feedback (Accept Nitrogen Action)
Log-Message "`n=== STEP 4: Submit User Feedback (Accept) ===" "INFO"

# Extract first action ID from response (if available)
$actionId = "a_${FieldId}_n"  # Default ID pattern

$feedbackPayload = @{
    field_id = $FieldId
    action_id = $actionId
    decision = "accepted"
    note = "Applied before forecasted rain event"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json -Depth 10

$feedbackResponse = Test-Endpoint -Method "POST" `
    -Url "$BaseUrl/cie/feedback" `
    -Body $feedbackPayload `
    -Description "Submit_Feedback_Accept"

Start-Sleep -Seconds 2

# Step 5: Get Field Status
Log-Message "`n=== STEP 5: Get Field Status Summary ===" "INFO"

$statusResponse = Test-Endpoint -Method "GET" `
    -Url "$BaseUrl/cie/field/status?field_id=$FieldId" `
    -Description "Get_Field_Status"

Start-Sleep -Seconds 1

# Step 6: Simulate Photo Upload
Log-Message "`n=== STEP 6: Simulate Photo Prompt Response ===" "INFO"

$photoPayload = @{
    field_id = $FieldId
    photo_date = "2025-12-22"
    stage_observed = "V6"
    notes = "Healthy 6-leaf stage, uniform emergence"
    quality = "good"
} | ConvertTo-Json -Depth 10

$photoResponse = Test-Endpoint -Method "POST" `
    -Url "$BaseUrl/cie/field/photo" `
    -Body $photoPayload `
    -Description "Submit_Photo_Observation"

# ==========================
# Test Summary
# ==========================

Log-Message "`n========================================" "INFO"
Log-Message "UAT Test Sequence Complete" "INFO"
Log-Message "========================================" "INFO"
Log-Message "Results saved to: $OutputDir" "INFO"
Log-Message "Log file: $logFile" "INFO"

# Quick validation checks
Log-Message "`n=== Validation Checks ===" "INFO"

$checks = @{
    "Field Registered" = $registerResponse -ne $null
    "Telemetry Accepted" = $telemetryResponse -ne $null
    "Actions Returned" = $actionsResponse -ne $null
    "Feedback Recorded" = $feedbackResponse -ne $null
    "Status Available" = $statusResponse -ne $null
    "Photo Recorded" = $photoResponse -ne $null
}

$passCount = 0
$totalCount = $checks.Count

foreach ($check in $checks.GetEnumerator()) {
    if ($check.Value) {
        Log-Message "  ✓ $($check.Key)" "PASS"
        $passCount++
    } else {
        Log-Message "  ✗ $($check.Key)" "FAIL"
    }
}

Log-Message "`nPassed: $passCount / $totalCount tests" "INFO"

if ($passCount -eq $totalCount) {
    Log-Message "🎉 All UAT tests passed!" "SUCCESS"
    exit 0
} else {
    Log-Message "⚠️ Some tests failed - review log for details" "WARNING"
    exit 1
}
