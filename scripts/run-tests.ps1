#!/usr/bin/env pwsh
# Test Runner for PreciagroMVP Temporal Logic Engine
# Run all organized tests from the tests directory

param(
    [string]$TestType = "all",  # Options: all, python, powershell, quick, comprehensive
    [switch]$Verbose,
    [switch]$SkipEnvironmentSetup
)

# Test execution functions (defined first)
function Run-PythonTest {
    param([string]$TestFile, [string]$Description)
    
    Write-Host "`n🐍 Running $Description..." -ForegroundColor Yellow
    Write-Host "   File: tests/$TestFile"
    
    # Set PYTHONPATH for proper imports
    $originalPath = $env:PYTHONPATH
    $env:PYTHONPATH = $PWD.Path
    
    try {
        if ($Verbose) {
            python "tests/$TestFile"
        } else {
            python "tests/$TestFile" 2>$null | Where-Object { $_ -match "✅|❌|🎉|Total tasks|Found.*rules|Testing.*Rule|Created.*task" }
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ PASSED" -ForegroundColor Green
        } else {
            Write-Host "   ❌ FAILED (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
        }
    } finally {
        # Restore original PYTHONPATH
        $env:PYTHONPATH = $originalPath
    }
}

function Run-PowerShellTest {
    param([string]$TestFile, [string]$Description)
    
    Write-Host "`n🔧 Running $Description..." -ForegroundColor Cyan
    Write-Host "   File: tests/$TestFile"
    
    if ($Verbose) {
        & "tests/$TestFile"
    } else {
        & "tests/$TestFile" 2>$null | Where-Object { $_ -match "✅|❌|SUCCESS|FAILED|Error" }
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ PASSED" -ForegroundColor Green
    } else {
        Write-Host "   ❌ FAILED (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
    }
}

Write-Host "🧪 PreciagroMVP Test Runner" -ForegroundColor Green
Write-Host ("=" * 50)

# Set environment variables if not skipping
if (-not $SkipEnvironmentSetup) {
    Write-Host "🔧 Setting up test environment..." -ForegroundColor Blue
    $env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    Write-Host "   DATABASE_URL set to in-memory SQLite"
}

# Main test execution
switch ($TestType.ToLower()) {
    "quick" {
        Write-Host "🚀 Running Quick Tests"
        Run-PowerShellTest "test_quick.ps1" "Quick Validation"
        Run-PythonTest "test_simple_engine.py" "Simple Engine Test"
    }
    
    "python" {
        Write-Host "🐍 Running Python Tests Only"
        Run-PythonTest "test_all_rules.py" "All Business Rules Test"
        Run-PythonTest "test_simple_engine.py" "Simple Engine Test"
        Run-PythonTest "test_engine_direct.py" "Direct Engine Test"
        Run-PythonTest "test_temporal_endpoints.py" "HTTP Endpoints Test"
    }
    
    "powershell" {
        Write-Host "🔧 Running PowerShell Tests Only"
        Run-PowerShellTest "test_all_endpoints.ps1" "All API Endpoints"
        Run-PowerShellTest "test_temporal_endpoints.ps1" "Temporal Endpoints"
        Run-PowerShellTest "test_real_engine.ps1" "Real Engine Test"
    }
    
    "comprehensive" {
        Write-Host "🎯 Running Comprehensive Test Suite"
        Run-PythonTest "test_all_rules.py" "All Business Rules Test (Comprehensive)"
        Run-PowerShellTest "test_all_endpoints.ps1" "All API Endpoints"
        Run-PowerShellTest "test_final.ps1" "Final Validation"
    }
    
    "all" {
        Write-Host "🌟 Running All Tests"
        
        Write-Host "`n📊 Core Engine Tests:" -ForegroundColor Magenta
        Run-PythonTest "test_all_rules.py" "All Business Rules"
        Run-PythonTest "test_simple_engine.py" "Simple Engine"
        Run-PythonTest "test_engine_direct.py" "Direct Engine"
        
        Write-Host "`n🌐 HTTP Integration Tests:" -ForegroundColor Magenta
        Run-PythonTest "test_temporal_endpoints.py" "Python HTTP Endpoints"
        Run-PowerShellTest "test_all_endpoints.ps1" "PowerShell All Endpoints"
        Run-PowerShellTest "test_temporal_endpoints.ps1" "PowerShell Temporal Endpoints"
        
        Write-Host "`n🚀 Quick Validation:" -ForegroundColor Magenta
        Run-PowerShellTest "test_quick.ps1" "Quick Tests"
        Run-PowerShellTest "test_final.ps1" "Final Validation"
    }
    
    default {
        Write-Host "❌ Invalid test type: $TestType" -ForegroundColor Red
        Write-Host "Valid options: all, python, powershell, quick, comprehensive"
        exit 1
    }
}

Write-Host "`n🏁 Test Run Complete!" -ForegroundColor Green
Write-Host "=" * 50

# Summary
Write-Host "`n📋 Available Test Commands:"
Write-Host "   .\run-tests.ps1 -TestType quick         # Fast validation"
Write-Host "   .\run-tests.ps1 -TestType python        # Python tests only"
Write-Host "   .\run-tests.ps1 -TestType powershell    # PowerShell tests only"
Write-Host "   .\run-tests.ps1 -TestType comprehensive # Key tests"
Write-Host "   .\run-tests.ps1 -TestType all           # Everything (default)"
Write-Host "   .\run-tests.ps1 -Verbose               # Detailed output"
