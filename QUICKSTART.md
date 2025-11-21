# 🚀 RealEstateGPT - Quick Start Guide

## ✅ What's Ready

Your AI-powered real estate chat agent is ready to test! All components are connected:

- ✅ **5 Tool Handlers** - Alias resolution, SQL/RPC, Analytics, CMA, CSV export
- ✅ **OpenAI Integration** - GPT-4o-mini with function calling
- ✅ **System Prompt** - Professional agent instructions
- ✅ **Orchestrator** - Multi-turn conversation loop
- ✅ **Test Suite** - Ready-to-run example queries

## 📋 Prerequisites

1. **Python 3.10+** installed
2. **OpenAI API Key** (get from https://platform.openai.com/api-keys)
3. **Supabase credentials** (already configured)

## 🏃 Quick Start (3 Steps)

### Step 1: Install Dependencies

```powershell
cd "C:\Users\wesle\OneDrive\Desktop\Dubai Real Estate Database"
pip install -r backend\requirements.txt
```

This installs:
- `openai>=1.0.0` - OpenAI Python SDK
- `rapidfuzz>=3.0.0` - Fuzzy string matching
- Plus all existing dependencies (pandas, requests, etc.)

### Step 2: Add OpenAI API Key

Create/edit `.env` file in the project root:

```env
# Supabase (already configured)
SUPABASE_URL=your_existing_url
SUPABASE_SERVICE_ROLE_KEY=your_existing_key
SUPABASE_DB_URL=your_existing_db_url

# OpenAI (ADD THIS)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

**Get your OpenAI key**: https://platform.openai.com/api-keys

### Step 3: Run Test

```powershell
cd backend\api
python chat_api.py
```

You should see output like:

```
🏠 RealEstateGPT Chat Agent
============================================================

🗣️  User: Who owns unit 504 in Business Bay?
------------------------------------------------------------
🤖 Assistant: Unit 504 in Business Bay is owned by...

🔧 Tools used (2):
   - resolve_alias: {'community': 'business bay'}
   - sql: {'rpc': 'search_owners', 'args': {...}}
============================================================
```

## 🧪 Test Queries

The test script runs these queries automatically:

1. **"Who owns unit 504 in Business Bay?"**
   - Tests: Alias resolution → Owner lookup
   
2. **"What's the average price in Downtown Dubai?"**
   - Tests: Community alias (Downtown → Burj Khalifa) → Market stats
   
3. **"Show me top 3 investors in Dubai Marina"**
   - Tests: SQL RPC function (top_investors)
   
4. **"Compare Business Bay vs Palm Jumeirah for price per sqft"**
   - Tests: Multi-community analytics

## 📊 Expected Results

### Query 1: Ownership Lookup
```
🔧 Tools used:
   - resolve_alias: Maps "business bay" to canonical name
   - sql: Calls search_owners RPC function

🤖 Response: Owner details with phone number (+971...)
```

### Query 2: Market Stats
```
🔧 Tools used:
   - resolve_alias: "downtown" → "Burj Khalifa"
   - sql: Calls market_stats RPC

🤖 Response: "23,564 transactions found in Burj Khalifa.
Average price: AED 3.5M, median: AED 2.8M..."
```

### Query 3: Top Investors
```
🔧 Tools used:
   - sql: Calls top_investors RPC

🤖 Response: Ranked list with property counts and values
```

### Query 4: Comparative Analysis
```
🔧 Tools used:
   - resolve_alias: (called twice, once per community)
   - compute: psf_stats operation

🤖 Response: Side-by-side comparison table
```

## 🔍 How It Works

```
User Query
    ↓
OpenAI (GPT-4o-mini)
    ↓
Function Calling → Tool Selection
    ↓
Tool Execution (your Python code)
    - resolve_alias()
    - run_sql_or_rpc()
    - run_compute()
    - generate_cma()
    - export_csv()
    ↓
Results → OpenAI
    ↓
Human-friendly Response
```

## 🎯 Interactive Testing

You can also test interactively by modifying `chat_api.py`:

```python
if __name__ == "__main__":
    # Interactive mode
    history = []
    
    while True:
        user_input = input("\n🗣️  You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        response, tools = chat_turn(history, user_input)
        print(f"🤖 Assistant: {response}")
        
        # Update history for multi-turn conversation
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})
```

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"
- Make sure `.env` file is in the project root
- Make sure you have `python-dotenv` installed
- Restart your terminal after editing `.env`

### "Module not found: backend.core.tools"
- Make sure you're running from the project root directory
- Check that `__init__.py` files exist in backend folders

### "Invalid API key"
- Double-check your OpenAI API key
- Make sure there are no extra spaces in `.env` file
- Try regenerating the key at https://platform.openai.com/api-keys

### "Supabase connection error"
- Check your existing Supabase credentials are still valid
- Test with: `python backend/core/tools.py`

## 📈 Cost Estimate

**GPT-4o-mini pricing** (as of 2024):
- Input: $0.150 per 1M tokens (~$0.0002 per request)
- Output: $0.600 per 1M tokens (~$0.001 per response)

**Typical query cost**: ~$0.001-0.005 (fraction of a cent)

For 1,000 queries: ~$1-5 USD

## 🚀 Next Steps

### 1. Build FastAPI Endpoint
Wrap `chat_turn()` in a REST API:

```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/chat")
async def chat(query: str, history: list = []):
    response, tools = chat_turn(history, query)
    return {"response": response, "tools": tools}
```

### 2. Create Frontend
Build a React chat interface:
- Send user messages to `/api/chat`
- Display responses with markdown
- Show tool usage for transparency

### 3. Add Multi-User Support
- User authentication (Supabase Auth)
- Conversation history per user
- User-specific permissions in `user_ctx`

### 4. Production Deployment
- Deploy backend to Railway/Render/AWS
- Deploy frontend to Vercel/Netlify
- Add rate limiting and monitoring

## 📚 Documentation

- **Full Implementation Guide**: `docs/CHAT_AGENT_IMPLEMENTATION.md`
- **System Prompt**: `backend/system_prompt.txt`
- **Tool Definitions**: `backend/core/tools.py`
- **Orchestrator**: `backend/api/chat_api.py`

## 🆘 Need Help?

1. Check the logs for detailed error messages
2. Review `docs/CHAT_AGENT_IMPLEMENTATION.md`
3. Test individual tools: `python backend/core/tools.py`
4. Verify environment variables: `python -c "from backend.config import *; print('✅ Config loaded')"`

---

**Status**: ✅ Ready to test!
**Next**: Run `python backend/api/chat_api.py` and see your AI agent in action!
