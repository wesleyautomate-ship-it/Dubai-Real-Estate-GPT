# Dubai Real Estate AI - Project Reorganization Script
# This script moves files to their proper locations

Write-Host "🚀 Starting Project Reorganization..." -ForegroundColor Cyan
Write-Host ""

# Create subdirectories
Write-Host "📁 Creating subdirectories..." -ForegroundColor Yellow
$directories = @(
    "database\schema",
    "database\migrations",
    "database\functions",
    "database\scripts"
)

foreach ($dir in $directories) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    Write-Host "  ✓ Created $dir" -ForegroundColor Green
}

Write-Host ""
Write-Host "📦 Moving Backend Files..." -ForegroundColor Yellow

# Backend Core Files
Move-Item -Path "real_estate_ai_orchestrator.py" -Destination "backend\core\ai_orchestrator.py" -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Moved ai_orchestrator.py" -ForegroundColor Green

Move-Item -Path "analytics_engine.py" -Destination "backend\core\analytics_engine.py" -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Moved analytics_engine.py" -ForegroundColor Green

# Backend Utils
Move-Item -Path "community_aliases.py" -Destination "backend\utils\community_aliases.py" -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Moved community_aliases.py" -ForegroundColor Green

Move-Item -Path "phone_utils.py" -Destination "backend\utils\phone_utils.py" -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Moved phone_utils.py" -ForegroundColor Green

Write-Host ""
Write-Host "💾 Moving Database Files..." -ForegroundColor Yellow

# Database Schema
Move-Item -Path "supabase_schema.sql" -Destination "database\schema\supabase_schema.sql" -Force -ErrorAction SilentlyContinue
Write-Host "  ✓ Moved supabase_schema.sql" -ForegroundColor Green

# Database Functions
$functionFiles = @(
    "supabase_rpc_functions.sql",
    "fix_rpc_functions_final.sql",
    "update_rpc_functions.sql"
)

foreach ($file in $functionFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "database\functions\$file" -Force
        Write-Host "  ✓ Moved $file" -ForegroundColor Green
    }
}

# Database Migrations
$migrationFiles = @(
    "convert_sqm_to_sqft.sql",
    "check_before_conversion.sql",
    "populate_community_aliases.sql"
)

foreach ($file in $migrationFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "database\migrations\$file" -Force
        Write-Host "  ✓ Moved $file" -ForegroundColor Green
    }
}

# Database Scripts
$scriptFiles = @(
    "ingest_dubai_real_estate.py",
    "populate_normalized_tables.py",
    "apply_rpc_functions.py",
    "validate_data.py",
    "fix_populate_all_data.py",
    "count_excel_rows.py"
)

foreach ($file in $scriptFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "database\scripts\$file" -Force
        Write-Host "  ✓ Moved $file" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "📚 Moving Documentation Files..." -ForegroundColor Yellow

$docFiles = @(
    "QUICK_REFERENCE.md",
    "IMPROVEMENTS_SUMMARY.md",
    "CONVERSION_INSTRUCTIONS.md",
    "COMMUNITY_NAMING_RESOLVED.md",
    "THINKING_ENGINE_GUIDE.md",
    "APPLY_RPC_INSTRUCTIONS.md",
    "TODO_CHECKLIST.md",
    "SYSTEM_COMPLETE.md"
)

foreach ($file in $docFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "docs\$file" -Force
        Write-Host "  ✓ Moved $file" -ForegroundColor Green
    }
}

# Copy README to docs (keep one in root too)
if (Test-Path "README.md") {
    Copy-Item -Path "README.md" -Destination "docs\README.md" -Force
    Write-Host "  ✓ Copied README.md to docs" -ForegroundColor Green
}

Write-Host ""
Write-Host "🧪 Moving Test Files..." -ForegroundColor Yellow

$testFiles = @(
    "test_analytics.py",
    "test_rpc_functions.py",
    "test_rpc_multiple_communities.py",
    "test_downtown_resolution.py",
    "demo_queries.py",
    "investigate_community_names.py",
    "cma_report_generator.py"
)

foreach ($file in $testFiles) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination "tests\$file" -Force
        Write-Host "  ✓ Moved $file" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "✅ Reorganization Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📌 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Run: python create_init_files.py" -ForegroundColor White
Write-Host "  2. Update imports in all files" -ForegroundColor White
Write-Host "  3. Test the reorganized structure" -ForegroundColor White
Write-Host ""
