"""
RealEstateGPT Chat API
OpenAI-powered conversational agent with function calling
"""

import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional
from pathlib import Path

from backend.core.tools import (
    resolve_alias,
    run_sql_or_rpc,
    run_compute,
    generate_cma,
    export_csv,
    semantic_search,
    TOOL_SCHEMAS
)
from backend.llm_client import get_llm_client

TZ = ZoneInfo("Asia/Dubai")

# Load system prompt
SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "system_prompt.txt"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text()


def chat_turn(
    history: List[Dict],
    user_text: str,
    user_ctx: Optional[Dict] = None,
    provider: Optional[str] = None,
) -> tuple[str, List[Dict], Dict[str, Any]]:
    """
    Process one conversational turn with tool calling.
    
    Args:
        history: Conversation history [{"role": "user/assistant", "content": "..."}]
        user_text: User's message
        user_ctx: User context (permissions, user_id, etc.)
        
    Returns:
        (response_text, tool_results)
        
    Example:
        response, tools = chat_turn([], "Who owns unit 504 in Business Bay?")
        print(response)  # "Unit 504 in Business Bay is owned by..."
        print(tools)     # [{"tool": "resolve_alias", "args": {...}, "result": {...}}]
    """
    if user_ctx is None:
        user_ctx = {}
    
    # Build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history + [
        {"role": "user", "content": user_text}
    ]
    
    # Initial API call
    llm = get_llm_client(provider)
    if not llm.supports_tool_calling:
        text = llm.simple_response(messages, temperature=0.2)
        return text, []

    start_time = datetime.now()
    response = llm.chat_completion(
        messages=messages,
        tools=TOOL_SCHEMAS,
        tool_choice="auto",
        temperature=0.2,
    )
    msg = response.choices[0].message
    tool_results: List[Dict[str, Any]] = []
    
    # Tool calling loop - continue until no more tool calls
    while msg.tool_calls:
        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments
                    }
                }
                for call in msg.tool_calls
            ]
        })
        
        # Execute each tool call
        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments or "{}")
            
            # Execute tool
            try:
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
                elif name == "semantic_search":
                    result = semantic_search(**args)
                else:
                    result = {"error": f"Unknown tool: {name}"}
            except Exception as e:
                result = {"error": str(e)}
            
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
                "content": json.dumps(result, default=str)[:15000]  # Limit size, handle datetime
            })
        
        # Call OpenAI again with tool results
        response = llm.chat_completion(
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )
        msg = response.choices[0].message
    
    # Return final answer
    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
    meta = {"provider": provider or "openai", "latency_ms": round(latency_ms, 2)}
    return msg.content, tool_results, meta


def chat_stream(
    history: List[Dict],
    user_text: str,
    user_ctx: Optional[Dict] = None,
    provider: Optional[str] = None,
):
    """
    Streaming version of chat_turn (for real-time UI updates).
    Yields chunks of the response as they arrive.
    
    Note: Tool calls are still executed synchronously, only the final
    answer is streamed.
    """
    # TODO: Implement streaming with tool calls
    # For now, just call chat_turn and yield the result
    response, tools, meta = chat_turn(history, user_text, user_ctx, provider=provider)
    if tools:
        yield {"type": "tools", "data": tools}
    yield {"type": "response", "data": response, "meta": meta}


# Example usage / testing
if __name__ == "__main__":
    print("🏠 RealEstateGPT Chat Agent")
    print("=" * 60)
    
    # Test queries
    test_queries = [
        "Who owns unit 504 in Business Bay?",
        "What's the average price in Downtown Dubai?",
        "Show me top 3 investors in Dubai Marina",
        "Compare Business Bay vs Palm Jumeirah for price per sqft"
    ]
    
    for query in test_queries:
        print(f"\n🗣️  User: {query}")
        print("-" * 60)
        
        try:
            response, tools = chat_turn([], query)
            
            print(f"🤖 Assistant: {response}\n")
            
            if tools:
                print(f"🔧 Tools used ({len(tools)}):")
                for t in tools:
                    print(f"   - {t['tool']}: {t['args']}")
                    if "error" in t.get("result", {}):
                        print(f"     ❌ Error: {t['result']['error']}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("=" * 60)
