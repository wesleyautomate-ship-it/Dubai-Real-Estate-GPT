"""
Complete Project Reorganization
Creates __init__.py files, config files, and updates all imports
"""

import os
import re

# Create __init__.py files
def create_init_files():
    """Create __init__.py in all Python package directories"""
    dirs = [
        "backend",
        "backend/api",
        "backend/core",
        "backend/utils",
        "tests"
    ]
    
    for dir_path in dirs:
        init_file = os.path.join(dir_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'"""{dir_path} package"""\n')
            print(f"✓ Created {init_file}")

# Create backend/config.py
def create_config():
    """Create configuration file"""
    config_content = '''"""
Backend Configuration
Manages environment variables and settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Database Configuration
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))

# Validate required variables
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is required")
if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

print("✓ Configuration loaded successfully")
'''
    
    with open("backend/config.py", 'w') as f:
        f.write(config_content)
    print("✓ Created backend/config.py")

# Create requirements.txt
def create_requirements():
    """Create requirements.txt"""
    requirements = '''# Dubai Real Estate AI - Backend Requirements

# Core Dependencies
requests>=2.31.0
pandas>=2.1.0
numpy>=1.24.0

# Database
psycopg2-binary>=2.9.9

# Analytics
scipy>=1.11.0
duckdb>=0.9.0

# API (FastAPI)
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.4.0

# Utilities
python-dotenv>=1.0.0
python-multipart>=0.0.6

# Development
pytest>=7.4.0
black>=23.10.0
'''
    
    with open("backend/requirements.txt", 'w') as f:
        f.write(requirements)
    print("✓ Created backend/requirements.txt")

# Create .env.example
def create_env_example():
    """Create .env.example template"""
    env_content = '''# Dubai Real Estate AI - Environment Variables

# Supabase Configuration
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres?sslmode=require

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database Configuration
DB_POOL_SIZE=10
'''
    
    with open(".env.example", 'w') as f:
        f.write(env_content)
    print("✓ Created .env.example")

# Create .gitignore
def create_gitignore():
    """Create .gitignore"""
    gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
*.env

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Data
.data_raw/
*.xlsx
*.csv
*.db

# Logs
*.log

# Frontend
frontend/node_modules/
frontend/dist/
frontend/.next/
'''
    
    with open(".gitignore", 'w') as f:
        f.write(gitignore_content)
    print("✓ Created .gitignore")

# Main execution
if __name__ == "__main__":
    print("🚀 Completing Project Reorganization...")
    print()
    
    print("📁 Creating __init__.py files...")
    create_init_files()
    print()
    
    print("⚙️  Creating configuration files...")
    create_config()
    create_requirements()
    create_env_example()
    create_gitignore()
    print()
    
    print("✅ Reorganization Complete!")
    print()
    print("📌 Next Steps:")
    print("  1. Install dependencies: pip install -r backend/requirements.txt")
    print("  2. Copy .env.example to .env and fill in your credentials")
    print("  3. Update imports in moved files (run update_imports.py)")
    print("  4. Test the reorganized structure")
    print()
