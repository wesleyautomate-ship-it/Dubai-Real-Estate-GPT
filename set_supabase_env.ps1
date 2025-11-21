# Supabase Environment Variable Setup Script
# Run this script after creating your Supabase project
# Usage: .\set_supabase_env.ps1

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Supabase Environment Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Prompt for credentials
$SupabaseURL = Read-Host "Enter your Supabase Project URL (e.g., https://xxxxx.supabase.co)"
$ServiceRoleKey = Read-Host "Enter your Supabase service_role key" -AsSecureString

# Convert SecureString to plain text for environment variable
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ServiceRoleKey)
$ServiceRoleKeyPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Set for current session
$env:SUPABASE_URL = $SupabaseURL
$env:SUPABASE_SERVICE_ROLE_KEY = $ServiceRoleKeyPlain

Write-Host ""
Write-Host "✅ Environment variables set for current PowerShell session" -ForegroundColor Green
Write-Host ""

# Ask if user wants to persist
$persist = Read-Host "Do you want to persist these for your Windows user account? (y/n)"

if ($persist -eq "y" -or $persist -eq "Y") {
    [Environment]::SetEnvironmentVariable("SUPABASE_URL", $SupabaseURL, "User")
    [Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", $ServiceRoleKeyPlain, "User")
    Write-Host "✅ Environment variables saved to Windows User environment" -ForegroundColor Green
    Write-Host "   They will be available in all future PowerShell sessions" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Variables only set for this session. Rerun this script in new terminals." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Verification:" -ForegroundColor Cyan
Write-Host "  SUPABASE_URL = $env:SUPABASE_URL" -ForegroundColor Gray
Write-Host "  SERVICE_ROLE_KEY = *****$(($env:SUPABASE_SERVICE_ROLE_KEY).Substring(($env:SUPABASE_SERVICE_ROLE_KEY).Length - 10))" -ForegroundColor Gray
Write-Host ""
Write-Host "Next step: Run the ingestion script with 'python ingest_dubai_real_estate.py'" -ForegroundColor Green
Write-Host ""
