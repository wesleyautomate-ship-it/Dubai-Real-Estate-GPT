"""
Update Imports After Reorganization
Automatically updates import statements in all moved files
"""

import os
import re

print("🔧 Updating imports in reorganized files...")
print()

# Define import replacements
replacements = {
    "from analytics_engine import": "from backend.core.analytics_engine import",
    "from community_aliases import": "from backend.utils.community_aliases import",
    "from phone_utils import": "from backend.utils.phone_utils import",
    "import analytics_engine": "from backend.core import analytics_engine",
    "import community_aliases": "from backend.utils import community_aliases",
    "import phone_utils": "from backend.utils import phone_utils",
}

# Files that need updating
files_to_update = [
    "backend/core/ai_orchestrator.py",
    "backend/core/analytics_engine.py",
    "tests/test_analytics.py",
    "tests/test_downtown_resolution.py",
]

updated_count = 0
error_count = 0

for file_path in files_to_update:
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        error_count += 1
        continue
    
    try:
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply replacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Updated {file_path}")
            updated_count += 1
        else:
            print(f"  No changes needed in {file_path}")
    
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        error_count += 1

print()
print(f"✅ Import update complete!")
print(f"   Files updated: {updated_count}")
if error_count > 0:
    print(f"   Errors: {error_count}")
print()
print("📌 Next: Test the imports with:")
print('   python -c "from backend.core import ai_orchestrator; print(\'OK!\')"')
print()
