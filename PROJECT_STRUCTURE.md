# Dubai Real Estate AI - Project Structure

## 📁 Organized Folder Structure

```
Dubai Real Estate Database/
│
├── backend/                          # Backend Python code
│   ├── api/                         # API endpoints and routes
│   │   └── chat_api.py              # Main chat API endpoint
│   │
│   ├── core/                        # Core business logic
│   │   ├── __init__.py
│   │   ├── ai_orchestrator.py       # Main AI brain
│   │   └── analytics_engine.py      # Analytics & calculations
│   │
│   ├── utils/                       # Utility modules
│   │   ├── __init__.py
│   │   ├── community_aliases.py     # Community name resolver
│   │   └── phone_utils.py           # Phone normalization
│   │
│   ├── config.py                    # Configuration management
│   └── requirements.txt             # Python dependencies
│
├── database/                         # Database scripts and schemas
│   ├── schema/
│   │   └── supabase_schema.sql     # Main database schema
│   │
│   ├── migrations/                  # Database migrations
│   │   ├── convert_sqm_to_sqft.sql
│   │   └── populate_community_aliases.sql
│   │
│   ├── functions/                   # RPC functions
│   │   ├── supabase_rpc_functions.sql
│   │   └── fix_rpc_functions_final.sql
│   │
│   └── scripts/                     # Utility scripts
│       ├── ingest_dubai_real_estate.py
│       ├── populate_normalized_tables.py
│       ├── apply_rpc_functions.py
│       └── validate_data.py
│
├── docs/                            # Documentation
│   ├── README.md                    # Main documentation
│   ├── QUICK_REFERENCE.md          # Quick reference guide
│   ├── API_DOCUMENTATION.md        # API docs
│   ├── IMPROVEMENTS_SUMMARY.md     # Change log
│   ├── CONVERSION_INSTRUCTIONS.md  # SQM to SQFT guide
│   ├── COMMUNITY_NAMING_RESOLVED.md
│   ├── THINKING_ENGINE_GUIDE.md
│   ├── APPLY_RPC_INSTRUCTIONS.md
│   ├── TODO_CHECKLIST.md
│   └── SYSTEM_COMPLETE.md
│
├── frontend/                        # Frontend application (to be built)
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── MessageList.jsx
│   │   │   └── InputBox.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── tests/                           # Test files
│   ├── test_analytics.py
│   ├── test_rpc_functions.py
│   ├── test_rpc_multiple_communities.py
│   ├── test_downtown_resolution.py
│   └── demo_queries.py
│
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
├── PROJECT_STRUCTURE.md            # This file
└── README.md                        # Main project README

```

## 📦 File Mapping (Old → New)

### Backend Files
- `real_estate_ai_orchestrator.py` → `backend/core/ai_orchestrator.py`
- `analytics_engine.py` → `backend/core/analytics_engine.py`
- `community_aliases.py` → `backend/utils/community_aliases.py`
- `phone_utils.py` → `backend/utils/phone_utils.py`
- `thinking_engine_orchestrator.py` → **DEPRECATED** (use ai_orchestrator.py)

### Database Files
- `supabase_schema.sql` → `database/schema/supabase_schema.sql`
- `supabase_rpc_functions.sql` → `database/functions/supabase_rpc_functions.sql`
- `fix_rpc_functions_final.sql` → `database/functions/fix_rpc_functions_final.sql`
- `update_rpc_functions.sql` → `database/functions/update_rpc_functions.sql`
- `convert_sqm_to_sqft.sql` → `database/migrations/convert_sqm_to_sqft.sql`
- `check_before_conversion.sql` → `database/migrations/check_before_conversion.sql`
- `populate_community_aliases.sql` → `database/migrations/populate_community_aliases.sql`
- `ingest_dubai_real_estate.py` → `database/scripts/ingest_dubai_real_estate.py`
- `populate_normalized_tables.py` → `database/scripts/populate_normalized_tables.py`
- `apply_rpc_functions.py` → `database/scripts/apply_rpc_functions.py`
- `validate_data.py` → `database/scripts/validate_data.py`
- `fix_populate_all_data.py` → `database/scripts/fix_populate_all_data.py`
- `count_excel_rows.py` → `database/scripts/count_excel_rows.py`

### Documentation Files
- `README.md` → `docs/README.md` (copy, keep one in root too)
- `QUICK_REFERENCE.md` → `docs/QUICK_REFERENCE.md`
- `IMPROVEMENTS_SUMMARY.md` → `docs/IMPROVEMENTS_SUMMARY.md`
- `CONVERSION_INSTRUCTIONS.md` → `docs/CONVERSION_INSTRUCTIONS.md`
- `COMMUNITY_NAMING_RESOLVED.md` → `docs/COMMUNITY_NAMING_RESOLVED.md`
- `THINKING_ENGINE_GUIDE.md` → `docs/THINKING_ENGINE_GUIDE.md`
- `APPLY_RPC_INSTRUCTIONS.md` → `docs/APPLY_RPC_INSTRUCTIONS.md`
- `TODO_CHECKLIST.md` → `docs/TODO_CHECKLIST.md`
- `SYSTEM_COMPLETE.md` → `docs/SYSTEM_COMPLETE.md`

### Test Files
- `test_analytics.py` → `tests/test_analytics.py`
- `test_rpc_functions.py` → `tests/test_rpc_functions.py`
- `test_rpc_multiple_communities.py` → `tests/test_rpc_multiple_communities.py`
- `test_downtown_resolution.py` → `tests/test_downtown_resolution.py`
- `demo_queries.py` → `tests/demo_queries.py`
- `investigate_community_names.py` → `tests/investigate_community_names.py`
- `cma_report_generator.py` → `tests/cma_report_generator.py`

### Root Files (Stay in Root)
- `.env` (create from .env.example)
- `.gitignore`
- `PROJECT_STRUCTURE.md`
- `README.md` (shortened version pointing to docs)
- `set_supabase_env.ps1` (convenient script)

## 🔧 Import Path Updates Required

After reorganization, imports will change:

### Before:
```python
from analytics_engine import AnalyticsEngine
from community_aliases import resolve_community_alias
from phone_utils import normalize_phone
```

### After:
```python
from backend.core.analytics_engine import AnalyticsEngine
from backend.utils.community_aliases import resolve_community_alias
from backend.utils.phone_utils import normalize_phone
```

## 🚀 Next Steps

1. ✅ Create folder structure
2. 🔄 Move files to new locations
3. 🔄 Update all import statements
4. 🔄 Create __init__.py files for Python packages
5. 🔄 Create backend/config.py
6. 🔄 Create backend/requirements.txt
7. 🔄 Create .env.example
8. 🔄 Create .gitignore
9. 🔄 Create simplified root README.md
10. ✅ Test all imports and connections

## 📝 Notes

- All Python files will be updated to use absolute imports from project root
- Database scripts will be updated to reference correct paths
- Tests will be updated to import from backend/ correctly
- Frontend will be initialized as a React/Vite project
- Documentation will be centralized in docs/ folder
