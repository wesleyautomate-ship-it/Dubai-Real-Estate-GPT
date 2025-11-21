# RealEstateGPT - Conversational Agent Implementation

## ✅ What's Been Built

### 1. Tool Handlers (`backend/core/tools.py`)
Complete implementation of all 5 agent tools:
- ✅ `resolve_alias` - Community/building name normalization
- ✅ `sql` (run_sql_or_rpc) - Safe Supabase RPC execution
- ✅ `compute` - Server-side analytics (7 operations)
- ✅ `cma_generate` - CMA report generation (stub)
- ✅ `export_list` (export_csv) - CSV export for outreach

### 2. System Prompt (`backend/system_prompt.txt`)
Professional agent instructions including:
- ✅ Buyer-first policy (default to current owners)
- ✅ Alias resolution requirement
- ✅ Asia/Dubai timezone
- ✅ Data quality rules
- ✅ Response formatting guidelines

### 3. Tool Schemas
OpenAI function calling schemas defined in `TOOL_SCHEMAS`

## 🔧 Next: Create the Orchestrator

Create `backend/api/chat_api.py`:

```python
"""
RealEstateGPT Chat API
OpenAI-powered conversational agent with function calling
"""

import os
import json
from openai import OpenAI
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Any

from backend.core.tools import (
    resolve_alias,
    run_sql_or_rpc,
    run_compute,
    generate_cma,
    export_csv,
    TOOL_SCHEMAS
)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TZ = ZoneInfo("Asia/Dubai")

# Load system prompt
SYSTEM_PROMPT = open("backend/system_prompt.txt").read()


def chat_turn(history: List[Dict], 
              user_text: str, 
              user_ctx: Dict = None) -> tuple[str, List[Dict]]:
    """
    Process one conversational turn with tool calling.
    
    Args:
        history: Conversation history
        user_text: User's message
        user_ctx: User context (permissions, etc.)
        
    Returns:
        (response_text, tool_results)
    """
    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history + [
        {"role": "user", "content": user_text}
    ]
    
    # Initial API call
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        temperature=0.2
    )
    
    msg = response.choices[0].message
    tool_results = []
    
    # Tool calling loop
    while msg.tool_calls:
        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            
            # Execute tool
            if name == "resolve_alias":
                result = resolve_alias(**args)
            elif name == "sql":
                result = run_sql_or_rpc(**args, user_ctx=user_ctx)
            elif name == "compute":
                result = run_compute(**args)
            elif name == "cma_generate":
                result = generate_cma(**args, user_ctx=user_ctx)
            elif name == "export_list":
                result = export_csv(**args, user_ctx=user_ctx)
            else:
                result = {"error": "Unknown tool"}
            
            tool_results.append({
                "tool": name,
                "args": args,
                "result": result
            })
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": name,
                "content": json.dumps(result)[:15000]  # Limit size
            })
        
        # Call OpenAI again with tool results
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2
        )
        msg = response.choices[0].message
    
    # Return final answer
    return msg.content, tool_results


# Example usage / testing
if __name__ == "__main__":
    # Test queries
    test_queries = [
        "Who owns unit 504 in Business Bay?",
        "What's the average price in Downtown Dubai?",
        "Show me top investors in Dubai Marina",
        "Compare Business Bay vs Palm Jumeirah for price per sqft"
    ]
    
    for query in test_queries:
        print(f"\n🗣️ User: {query}")
        print("-" * 60)
        
        response, tools = chat_turn([], query)
        
        print(f"🤖 Assistant: {response}")
        print(f"\n🔧 Tools used: {[t['tool'] for t in tools]}")
        print("=" * 60)
```

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install openai python-dotenv rapidfuzz
```

### 2. Set Environment Variables
Add to your `.env`:
```
OPENAI_API_KEY=your_openai_key_here
```

### 3. Test the Agent
```powershell
cd backend/api
python chat_api.py
```

## 📊 Example Flows

### Flow 1: Ownership Lookup
**User**: "Who owns unit 1504 in Orla?"

**Agent executes**:
1. `resolve_alias(community="orla")` → "Orla Residences"
2. `sql(rpc="search_owners", args={"query": "..."})` or query properties table
3. Composes answer with owner name, phone, last price

### Flow 2: Market Stats with Alias
**User**: "Average price in downtown?"

**Agent executes**:
1. `resolve_alias(community="downtown")` → "Burj Khalifa"
2. `sql(rpc="market_stats", args={"p_community": "Burj Khalifa"})`
3. Summarizes: "23,564 transactions, avg AED 3.5M..."

### Flow 3: Comparative Analysis
**User**: "Compare Business Bay vs Palm for PSF"

**Agent executes**:
1. `resolve_alias` for both communities
2. `compute(op="psf_stats", payload={...})` for each
3. Presents comparison table

### Flow 4: Property List + Export
**User**: "Find 2BR 1600-1900 sqft in City Walk, export CSV"

**Agent executes**:
1. `resolve_alias(community="city walk")`
2. Query properties/transactions
3. `export_list(columns=[...], rows=[...], filename="city_walk_2br")`
4. Returns CSV path

## 🔐 Security Notes

### Already Implemented:
- ✅ Server-side only tool execution
- ✅ No direct SQL (RPC only)
- ✅ Credentials in environment variables
- ✅ Tool result size limits (15KB)

### To Add:
- User context/permissions in `user_ctx`
- Rate limiting per user
- Audit logging of tool calls
- Row-level security (RLS) in Supabase

## 📝 Testing Checklist

- [ ] Test alias resolution ("downtown" → "Burj Khalifa")
- [ ] Test RPC calls (market_stats, top_investors)
- [ ] Test compute operations (trend, comps)
- [ ] Test multi-turn conversations
- [ ] Test error handling (bad community name)
- [ ] Test CSV export
- [ ] Test with real OpenAI key

## 🎯 Integration Points

### With Existing Code:
- ✅ Uses `backend.utils.community_aliases`
- ✅ Uses `backend.core.analytics_engine`
- ✅ Uses Supabase RPC functions
- ✅ Consistent with project structure

### With Frontend (Next Step):
- Chat UI sends user message → `/api/chat` endpoint
- Backend runs `chat_turn(history, message, user_ctx)`
- Returns `{response, tools_used}` to frontend
- Frontend displays response, updates history

## 📚 Available Operations

### SQL Tool (RPC Functions):
- `market_stats` - Market statistics
- `top_investors` - Top property owners
- `owner_portfolio` - Owner's properties
- `find_comparables` - Comparable sales
- `transaction_velocity` - Market velocity
- `search_owners` - Owner search
- `likely_sellers` - Prospecting
- `seasonal_patterns` - Seasonality
- `compare_communities` - Community comparison
- `property_history` - Transaction history

### Compute Tool:
- `psf_stats` - Price per sqft analysis
- `trend` - Growth rate trends
- `comps` - Comparable properties
- `correlation` - Community correlation
- `likely_sellers` - Hold duration analysis
- `velocity` - Transaction velocity
- `top_investors` - Investor intelligence

## 🔄 Next Steps

1. **Create FastAPI wrapper** (`backend/api/chat_api.py` as FastAPI endpoint)
2. **Add conversation persistence** (store in Supabase)
3. **Build frontend chat interface** (React + Vite)
4. **Add user authentication** (Supabase Auth)
5. **Deploy to production** (Railway/Vercel/AWS)

---

**Status**: ✅ Tools & System Prompt Complete
**Next**: Create FastAPI endpoint + Test with OpenAI
**File**: See `backend/core/tools.py` for implementation
