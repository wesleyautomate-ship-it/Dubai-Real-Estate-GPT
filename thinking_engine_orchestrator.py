"""
Thinking Market Engine - AI Orchestration Layer
Routes natural language queries to appropriate analytical skills
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}


class ThinkingEngine:
    """
    AI-powered market analysis engine that routes queries to appropriate skills
    """
    
    # Define available analytical skills
    SKILLS = {
        "market_stats": {
            "description": "Get market statistics (avg price, median, volume, etc.) for a community or property type",
            "params": ["community", "property_type", "bedrooms", "start_date", "end_date"]
        },
        "top_investors": {
            "description": "Find top investors/owners by portfolio value and property count",
            "params": ["community", "limit", "min_properties"]
        },
        "owner_portfolio": {
            "description": "Get all properties owned by a specific person or entity",
            "params": ["owner_name", "owner_phone"]
        },
        "find_comparables": {
            "description": "Find comparable properties for CMA (price comparison)",
            "params": ["community", "property_type", "bedrooms", "size_sqft", "months_back", "limit"]
        },
        "transaction_velocity": {
            "description": "Get transaction volume trends over time (monthly)",
            "params": ["community", "months"]
        },
        "seasonal_patterns": {
            "description": "Analyze seasonal transaction patterns (which months are busiest)",
            "params": ["community"]
        },
        "likely_sellers": {
            "description": "Find properties owned for 3+ years (prospecting opportunities)",
            "params": ["community", "min_years_owned", "limit"]
        },
        "compare_communities": {
            "description": "Compare multiple communities side-by-side",
            "params": ["communities"]
        },
        "property_history": {
            "description": "Get full transaction history for a specific property",
            "params": ["community", "building", "unit"]
        },
        "search_owners": {
            "description": "Search for owners by name or phone number",
            "params": ["query", "limit"]
        },
        "generate_cma_report": {
            "description": "Generate a comprehensive CMA report with PDF and CSV exports",
            "params": ["community", "property_type", "bedrooms", "size_sqft"]
        },
        "investor_list_export": {
            "description": "Export top investors list to CSV with contact information",
            "params": ["community", "min_properties"]
        }
    }
    
    def __init__(self, use_ai=True):
        """
        Initialize the Thinking Engine
        
        Args:
            use_ai: Whether to use OpenAI for intent parsing (requires API key)
        """
        self.use_ai = use_ai and bool(os.getenv("OPENAI_API_KEY"))
        if not self.use_ai:
            print("⚠️  Running in non-AI mode (keyword matching only)")
    
    def parse_intent(self, query: str) -> Dict[str, Any]:
        """
        Parse user query to determine intent and extract parameters
        
        Args:
            query: Natural language query
            
        Returns:
            Dictionary with skill name and parameters
        """
        if self.use_ai:
            return self._parse_intent_ai(query)
        else:
            return self._parse_intent_keyword(query)
    
    def _parse_intent_ai(self, query: str) -> Dict[str, Any]:
        """Use OpenAI to parse intent"""
        
        # Build function calling schema
        functions = []
        for skill_name, skill_info in self.SKILLS.items():
            properties = {}
            for param in skill_info["params"]:
                if param in ["community", "building", "unit", "owner_name", "property_type", "query"]:
                    properties[param] = {"type": "string"}
                elif param in ["bedrooms", "limit", "months", "min_properties", "min_years_owned"]:
                    properties[param] = {"type": "integer"}
                elif param in ["size_sqft"]:
                    properties[param] = {"type": "number"}
                elif param == "communities":
                    properties[param] = {"type": "array", "items": {"type": "string"}}
                elif param in ["start_date", "end_date"]:
                    properties[param] = {"type": "string", "description": "Date in YYYY-MM-DD format"}
                elif param in ["owner_phone"]:
                    properties[param] = {"type": "string", "description": "Phone number"}
            
            functions.append({
                "type": "function",
                "function": {
                    "name": skill_name,
                    "description": skill_info["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties
                    }
                }
            })
        
        # Call OpenAI with function calling
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI assistant for Dubai real estate market analysis. Parse user queries and route them to appropriate analytical functions."},
                    {"role": "user", "content": query}
                ],
                tools=functions,
                tool_choice="auto"
            )
            
            # Extract function call
            if response.choices[0].message.tool_calls:
                tool_call = response.choices[0].message.tool_calls[0]
                return {
                    "skill": tool_call.function.name,
                    "params": json.loads(tool_call.function.arguments),
                    "confidence": "high"
                }
            else:
                # No function called - general question
                return {
                    "skill": "general_chat",
                    "params": {},
                    "response": response.choices[0].message.content
                }
        
        except Exception as e:
            print(f"⚠️  AI parsing failed: {e}")
            return self._parse_intent_keyword(query)
    
    def _parse_intent_keyword(self, query: str) -> Dict[str, Any]:
        """Simple keyword-based intent parsing"""
        query_lower = query.lower()
        
        # Market stats
        if any(word in query_lower for word in ["average price", "market stats", "statistics", "median price"]):
            return {
                "skill": "market_stats",
                "params": self._extract_params(query),
                "confidence": "medium"
            }
        
        # Top investors
        if any(word in query_lower for word in ["top investor", "biggest owner", "portfolio"]):
            return {
                "skill": "top_investors",
                "params": {"limit": 10},
                "confidence": "medium"
            }
        
        # Comparables
        if any(word in query_lower for word in ["comparable", "similar propert", "cma"]):
            return {
                "skill": "find_comparables",
                "params": self._extract_params(query),
                "confidence": "medium"
            }
        
        # Transaction velocity
        if any(word in query_lower for word in ["transaction volume", "velocity", "trend"]):
            return {
                "skill": "transaction_velocity",
                "params": {"months": 12},
                "confidence": "medium"
            }
        
        # Default to market stats
        return {
            "skill": "market_stats",
            "params": self._extract_params(query),
            "confidence": "low"
        }
    
    def _extract_params(self, query: str) -> Dict[str, Any]:
        """Extract common parameters from query"""
        params = {}
        
        # Extract community names
        communities = ["Business Bay", "Dubai Marina", "Downtown Dubai", "JVC", "Arabian Ranches", 
                      "Palm Jumeirah", "Dubai Creek Harbour", "Dubai Hills", "JBR", "Damac Hills"]
        for community in communities:
            if community.lower() in query.lower():
                params["community"] = community
                break
        
        # Extract bedroom count
        for i in range(1, 6):
            if f"{i} bedroom" in query.lower() or f"{i}br" in query.lower():
                params["bedrooms"] = i
                break
        
        return params
    
    def execute_skill(self, skill: str, params: Dict[str, Any]) -> Any:
        """
        Execute the identified skill with parameters
        
        Args:
            skill: Skill name
            params: Parameters for the skill
            
        Returns:
            Skill execution result
        """
        if skill == "generate_cma_report":
            return self._generate_cma_report(params)
        elif skill == "investor_list_export":
            return self._generate_investor_list(params)
        elif skill == "general_chat":
            return params.get("response", "I'm not sure how to help with that.")
        else:
            # Call Supabase RPC function
            return self._call_rpc_function(skill, params)
    
    def _call_rpc_function(self, function_name: str, params: Dict[str, Any]) -> Any:
        """Call a Supabase RPC function"""
        url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
        
        # Prefix parameters with p_
        rpc_params = {f"p_{k}": v for k, v in params.items()}
        
        try:
            response = requests.post(url, headers=HEADERS, json=rpc_params)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"RPC call failed: {response.status_code}", "details": response.text}
        except Exception as e:
            return {"error": str(e)}
    
    def _generate_cma_report(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Generate CMA report"""
        from cma_report_generator import CMAReportGenerator
        
        cma = CMAReportGenerator(
            community=params.get("community", ""),
            property_type=params.get("property_type"),
            bedrooms=params.get("bedrooms"),
            size_sqft=params.get("size_sqft")
        )
        
        if cma.fetch_data():
            pdf_path = cma.generate_pdf(f"CMA_{params.get('community', 'Report')}.pdf")
            csv_path = cma.generate_csv(f"CMA_{params.get('community', 'Report')}_Comparables.csv")
            return {
                "success": True,
                "pdf": pdf_path,
                "csv": csv_path,
                "message": f"CMA report generated for {params.get('community')}"
            }
        else:
            return {"success": False, "message": "Failed to fetch data"}
    
    def _generate_investor_list(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Generate investor list CSV"""
        from cma_report_generator import generate_investor_list_csv
        
        csv_path = generate_investor_list_csv(
            community=params.get("community"),
            min_properties=params.get("min_properties", 3),
            output_path="Top_Investors.csv"
        )
        
        if csv_path:
            return {
                "success": True,
                "csv": csv_path,
                "message": "Investor list exported"
            }
        else:
            return {"success": False, "message": "Failed to generate list"}
    
    def format_response(self, skill: str, result: Any) -> str:
        """
        Format skill execution result into natural language
        
        Args:
            skill: Skill that was executed
            result: Result from skill execution
            
        Returns:
            Natural language response
        """
        if isinstance(result, dict) and "error" in result:
            return f"❌ Error: {result['error']}"
        
        # Format based on skill type
        if skill == "market_stats":
            if isinstance(result, list) and len(result) > 0:
                stats = result[0]
                return f"""
📊 Market Statistics:
• Average Price: AED {stats.get('avg_price', 0):,.0f}
• Median Price: AED {stats.get('median_price', 0):,.0f}
• Price Range: AED {stats.get('min_price', 0):,.0f} - AED {stats.get('max_price', 0):,.0f}
• Total Transactions: {stats.get('total_transactions', 0):,}
• Total Volume: AED {stats.get('total_volume', 0):,.0f}
• Avg Price/SqFt: AED {stats.get('avg_price_per_sqft', 0):,.0f}
"""
        
        elif skill == "top_investors":
            if isinstance(result, list) and len(result) > 0:
                response = "🏢 Top Investors:\n\n"
                for i, investor in enumerate(result[:10], 1):
                    response += f"{i}. {investor['owner_name']}\n"
                    response += f"   Properties: {investor['total_properties']}\n"
                    response += f"   Portfolio Value: AED {investor['portfolio_value']:,.0f}\n"
                    response += f"   Phone: {investor['owner_phone']}\n\n"
                return response
        
        elif skill == "find_comparables":
            if isinstance(result, list) and len(result) > 0:
                response = f"🏘️  Found {len(result)} Comparable Properties:\n\n"
                for i, comp in enumerate(result[:5], 1):
                    response += f"{i}. {comp['building']} - Unit {comp['unit']}\n"
                    response += f"   Price: AED {comp['price']:,.0f} ({comp['bedrooms']} BR, {comp['size_sqft']:,.0f} sqft)\n"
                    response += f"   Price/SqFt: AED {comp['price_per_sqft']:,.0f}\n"
                    response += f"   Date: {comp['transaction_date']}\n\n"
                return response
        
        elif skill == "transaction_velocity":
            if isinstance(result, list) and len(result) > 0:
                response = "📈 Transaction Velocity:\n\n"
                for month in result[:6]:
                    response += f"{month['year_month']}: {month['transaction_count']} transactions (AED {month['total_volume']:,.0f})\n"
                return response
        
        elif skill == "generate_cma_report":
            if result.get("success"):
                return f"✅ CMA Report Generated!\n📄 PDF: {result['pdf']}\n📊 CSV: {result['csv']}"
            else:
                return f"❌ {result.get('message')}"
        
        # Default JSON response
        return json.dumps(result, indent=2)
    
    def chat(self, query: str) -> str:
        """
        Main chat interface - process a query end-to-end
        
        Args:
            query: Natural language query
            
        Returns:
            Natural language response
        """
        print(f"\n🤔 Query: {query}\n")
        
        # 1. Parse intent
        intent = self.parse_intent(query)
        print(f"🎯 Intent: {intent['skill']} (confidence: {intent.get('confidence', 'N/A')})")
        print(f"📋 Parameters: {intent.get('params', {})}\n")
        
        # 2. Execute skill
        result = self.execute_skill(intent["skill"], intent.get("params", {}))
        
        # 3. Format response
        response = self.format_response(intent["skill"], result)
        
        return response


# CLI Interface
def main():
    """Interactive CLI for the Thinking Engine"""
    print("="*60)
    print("🏢 DUBAI REAL ESTATE - THINKING MARKET ENGINE")
    print("="*60)
    print("\nAsk me anything about Dubai real estate:")
    print("  • Market statistics")
    print("  • Top investors")
    print("  • Comparable properties")
    print("  • Transaction trends")
    print("  • Generate CMA reports")
    print("\nType 'exit' to quit\n")
    
    engine = ThinkingEngine(use_ai=True)
    
    while True:
        try:
            query = input("You: ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "bye"]:
                print("Goodbye! 👋")
                break
            
            response = engine.chat(query)
            print(f"\nAssistant: {response}\n")
            print("-"*60)
        
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    # Test examples
    engine = ThinkingEngine(use_ai=False)  # Non-AI mode for testing
    
    print("Testing Thinking Engine...")
    print("="*60)
    
    # Test 1: Market stats
    print(engine.chat("What are the average prices in Business Bay?"))
    
    # Test 2: Top investors
    print(engine.chat("Who are the top investors in Dubai?"))
    
    # Test 3: Comparables
    print(engine.chat("Find comparable 2 bedroom apartments in Dubai Marina"))
