# ================================
# Git Push Helper Script for PowerShell (with memory)
# ================================

# Step 1: Navigate to your folder (CHANGE THIS TO YOUR PROJECT PATH)
$projectPath = "C:\Users\tmadz\Documents\Weather module preciagro"
Set-Location $projectPath

# Path to store config
$configFile = ".gitpushconfig"

# Step 2: Initialize Git if not already initialized
if (-not (Test-Path ".git")) {
    git init
}

# Step 3: Load saved config if it exists
$branch = ""
$repo = ""

if (Test-Path $configFile) {
    $savedConfig = Get-Content $configFile | ConvertFrom-Json
    $branch = $savedConfig.branch
    $repo = $savedConfig.repo

    Write-Host "Last used branch: $branch"
    Write-Host "Last used repo: $repo"
}

# Step 4: Ask for branch (use saved if available)
if (-not $branch) {
    $branch = Read-Host "Enter the branch you want to push to"
} else {
    $useSavedBranch = Read-Host "Use last branch '$branch'? (Y/N)"
    if ($useSavedBranch -match "^[Nn]") {
        $branch = Read-Host "Enter new branch"
    }
}

# Step 5: Switch/create branch
git checkout -B $branch

# Step 6: Add files
git add .

# Step 7: Commit
$commitMessage = Read-Host "Enter commit message"
git commit -m "$commitMessage"

# Step 8: Ask for repo (use saved if available)
if (-not $repo) {
    $repo = Read-Host "Enter your GitHub repo URL"
} else {
    $useSavedRepo = Read-Host "Use last repo '$repo'? (Y/N)"
    if ($useSavedRepo -match "^[Nn]") {
        $repo = Read-Host "Enter new repo URL"
    }
}

# Step 9: Add or update origin
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    git remote set-url origin $repo
} else {
    git remote add origin $repo
}

# Step 10: Push
git push -u origin $branch

# Step 11: Save config
@{branch = $branch; repo = $repo} | ConvertTo-Json | Set-Content $configFile
