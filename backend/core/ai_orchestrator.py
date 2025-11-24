"""
Dubai Real Estate AI Orchestrator
==================================
The "brain" that routes natural language queries to the right data sources
and returns conversational, intelligent responses.

Core capabilities:
- Intent classification (what is the user asking?)
- Query routing (which RPC function or analytics method?)
- Context memory (remembers last query per user)
- Natural language response generation
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import requests
from backend.core.analytics_engine import AnalyticsEngine
from backend.utils.community_aliases import resolve_community_alias
from backend.utils.phone_utils import normalize_phone

# Neon REST configuration (falls back to Supabase env vars for compatibility)
NEON_REST_URL = os.getenv("NEON_REST_URL") or os.getenv("NEON_REST_URL")
NEON_SERVICE_ROLE_KEY = os.getenv("NEON_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

HEADERS = {
    "apikey": NEON_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {NEON_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}


class RealEstateAI:
    """
    The conversational AI orchestrator for Dubai real estate data.
    Understands natural language and routes to appropriate data sources.
    """
    
    def __init__(self):
        self.analytics = AnalyticsEngine()
        self.context = {}  # Per-user context memory
        
    def process_query(self, user_query: str, user_id: str = "default") -> Dict:
        """
        Main entry point: process a natural language query
        
        Args:
            user_query: Natural language question from user
            user_id: User identifier for context memory
            
        Returns:
            {
                "intent": "ownership_lookup",
                "data": {...},
                "response": "Natural language answer",
                "metadata": {...}
            }
        """
        # Store query in context
        if user_id not in self.context:
            self.context[user_id] = {"history": []}
        
        self.context[user_id]["history"].append({
            "query": user_query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Classify intent
        intent = self._classify_intent(user_query)
        
        # Route to appropriate handler
        handler = self._get_handler(intent)
        result = handler(user_query, user_id)
        
        # Update context with result
        self.context[user_id]["last_query"] = user_query
        self.context[user_id]["last_intent"] = intent
        self.context[user_id]["last_result"] = result
        
        return result
    
    def _classify_intent(self, query: str) -> str:
        """
        Classify user intent from natural language query
        
        Returns one of:
        - ownership_lookup
        - transaction_history
        - property_finder
        - owner_portfolio
        - market_stats
        - comparables
        - market_trends
        - top_investors
        - likely_sellers
        - transaction_velocity
        - community_comparison
        - owner_discovery
        - learning
        """
        query_lower = query.lower()
        
        # Ownership patterns
        if any(word in query_lower for word in ["who owns", "owner of", "current owner"]):
            return "ownership_lookup"
        
        # Transaction history
        if any(word in query_lower for word in ["history", "previous owner", "sold before", "bought before"]):
            return "transaction_history"
        
        # Property finder (size/type based)
        if any(word in query_lower for word in ["find", "list", "show me"]) and \
           any(word in query_lower for word in ["bed", "sqft", "apartment", "villa"]):
            return "property_finder"
        
        # Owner portfolio
        if any(word in query_lower for word in ["portfolio", "properties owned", "what does", "what properties"]):
            return "owner_portfolio"
        
        # Market statistics
        if any(word in query_lower for word in ["average price", "market stats", "how much", "price in"]):
            return "market_stats"
        
        # Comparables / valuation
        if any(word in query_lower for word in ["comparable", "cma", "estimate", "valuation", "worth"]):
            return "comparables"
        
        # Market trends
        if any(word in query_lower for word in ["trend", "growth", "changed", "appreciation"]):
            return "market_trends"
        
        # Top investors
        if any(word in query_lower for word in ["top investor", "most properties", "biggest owner"]):
            return "top_investors"
        
        # Likely sellers
        if any(word in query_lower for word in ["likely sell", "bought years ago", "long holding"]):
            return "likely_sellers"
        
        # Transaction velocity
        if any(word in query_lower for word in ["velocity", "transaction rate", "how often", "turnover"]):
            return "transaction_velocity"
        
        # Community comparison
        if any(word in query_lower for word in ["compare", "vs", "versus", "which community"]):
            return "community_comparison"
        
        # Owner discovery
        if any(word in query_lower for word in ["owners of", "owner list", "contact details"]):
            return "owner_discovery"
        
        # Learning / explanation
        if any(word in query_lower for word in ["explain", "what is", "how does", "tell me about"]):
            return "learning"
        
        # Default to market stats
        return "market_stats"
    
    def _get_handler(self, intent: str):
        """Get the appropriate handler function for an intent"""
        handlers = {
            "ownership_lookup": self._handle_ownership_lookup,
            "transaction_history": self._handle_transaction_history,
            "property_finder": self._handle_property_finder,
            "owner_portfolio": self._handle_owner_portfolio,
            "market_stats": self._handle_market_stats,
            "comparables": self._handle_comparables,
            "market_trends": self._handle_market_trends,
            "top_investors": self._handle_top_investors,
            "likely_sellers": self._handle_likely_sellers,
            "transaction_velocity": self._handle_transaction_velocity,
            "community_comparison": self._handle_community_comparison,
            "owner_discovery": self._handle_owner_discovery,
            "learning": self._handle_learning
        }
        
        return handlers.get(intent, self._handle_market_stats)
    
    # ========== INTENT HANDLERS ==========
    
    def _handle_ownership_lookup(self, query: str, user_id: str) -> Dict:
        """Handle: 'Who owns unit 504 in Orla?'"""
        # Extract community, building, unit
        community = self._extract_community(query)
        unit = self._extract_unit(query)
        
        # Query v_current_owner
        url = f"{NEON_REST_URL}/rest/v1/v_current_owner"
        params = {
            "select": "*",
            "limit": "1"
        }
        
        if community:
            params["community"] = f"ilike.%{community}%"
        if unit:
            params["unit"] = f"ilike.%{unit}%"
        
        resp = requests.get(url, params=params, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                owner = data[0]
                response = f"Unit {owner['unit']} in {owner['community']} is owned by **{owner['owner_name']}**"
                if owner.get('owner_phone'):
                    response += f" (📞 {owner['owner_phone']})"
                if owner.get('last_price'):
                    response += f". Purchased for AED {owner['last_price']:,.0f}"
                if owner.get('last_transfer_date'):
                    response += f" on {owner['last_transfer_date']}"
                response += "."
                
                return {
                    "intent": "ownership_lookup",
                    "data": owner,
                    "response": response,
                    "metadata": {"source": "v_current_owner"}
                }
        
        return {
            "intent": "ownership_lookup",
            "data": None,
            "response": "Sorry, I couldn't find ownership information for that property.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_transaction_history(self, query: str, user_id: str) -> Dict:
        """Handle: 'Show me the transaction history for unit 403'"""
        community = self._extract_community(query)
        unit = self._extract_unit(query)
        
        # Use RPC function or query transactions table
        url = f"{NEON_REST_URL}/rest/v1/transactions"
        params = {
            "select": "transaction_date,seller_name,buyer_name,price",
            "order": "transaction_date.desc",
            "limit": "10"
        }
        
        if community:
            params["community"] = f"ilike.%{community}%"
        if unit:
            params["unit"] = f"ilike.%{unit}%"
        
        resp = requests.get(url, params=params, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                response = f"Transaction history for {unit} in {community}:\n\n"
                for i, txn in enumerate(data, 1):
                    response += f"{i}. {txn['transaction_date']}: {txn['buyer_name']} bought from {txn['seller_name']} for AED {txn['price']:,.0f}\n"
                
                return {
                    "intent": "transaction_history",
                    "data": data,
                    "response": response,
                    "metadata": {"count": len(data)}
                }
        
        return {
            "intent": "transaction_history",
            "data": [],
            "response": "No transaction history found.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_property_finder(self, query: str, user_id: str) -> Dict:
        """Handle: 'Find 2-bed apartments between 1500-1900 sqft in City Walk'"""
        # Extract parameters
        community = self._extract_community(query)
        bedrooms = self._extract_bedrooms(query)
        size_range = self._extract_size_range(query)
        
        # Query properties table
        url = f"{NEON_REST_URL}/rest/v1/properties"
        params = {
            "select": "community,building,unit,type,bedrooms,size_sqft,owner_id",
            "limit": "50"
        }
        
        if community:
            community = resolve_community_alias(community)
            params["community"] = f"ilike.%{community}%"
        if bedrooms:
            params["bedrooms"] = f"eq.{bedrooms}"
        if size_range:
            params["size_sqft"] = f"gte.{size_range[0]}"
            params["size_sqft"] = f"lte.{size_range[1]}"
        
        resp = requests.get(url, params=params, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                response = f"Found {len(data)} properties matching your criteria:\n\n"
                for i, prop in enumerate(data[:10], 1):
                    response += f"{i}. {prop['community']} - {prop['building']}, Unit {prop['unit']} ({prop['bedrooms']} bed, {prop['size_sqft']:.0f} sqft)\n"
                
                if len(data) > 10:
                    response += f"\n... and {len(data) - 10} more."
                
                return {
                    "intent": "property_finder",
                    "data": data,
                    "response": response,
                    "metadata": {"count": len(data)}
                }
        
        return {
            "intent": "property_finder",
            "data": [],
            "response": "No properties found matching those criteria.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_owner_portfolio(self, query: str, user_id: str) -> Dict:
        """Handle: 'What properties does Ayesha Ahmed own?'"""
        # Extract owner name or phone
        owner_name = self._extract_owner_name(query)
        phone = self._extract_phone(query)
        
        if phone:
            phone = normalize_phone(phone)
        
        # Use owner_portfolio RPC or query
        url = f"{NEON_REST_URL}/rest/v1/rpc/owner_portfolio"
        payload = {}
        
        if owner_name:
            payload["p_owner_name"] = owner_name
        if phone:
            payload["p_owner_phone"] = phone
        
        resp = requests.post(url, json=payload, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                response = f"**{owner_name or 'Owner'}** owns {len(data)} properties:\n\n"
                total_value = sum(p.get('last_price', 0) or 0 for p in data)
                
                for i, prop in enumerate(data[:10], 1):
                    response += f"{i}. {prop['community']} - {prop['building']}, Unit {prop['unit']}"
                    if prop.get('last_price'):
                        response += f" (AED {prop['last_price']:,.0f})"
                    response += "\n"
                
                if total_value > 0:
                    response += f"\n**Total Portfolio Value:** AED {total_value:,.0f}"
                
                return {
                    "intent": "owner_portfolio",
                    "data": data,
                    "response": response,
                    "metadata": {"count": len(data), "total_value": total_value}
                }
        
        return {
            "intent": "owner_portfolio",
            "data": [],
            "response": "Owner not found or no properties recorded.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_market_stats(self, query: str, user_id: str) -> Dict:
        """Handle: 'What's the average price in Business Bay?'"""
        community = self._extract_community(query)
        
        if community:
            community = resolve_community_alias(community)
        
        # Use RPC function
        url = f"{NEON_REST_URL}/rest/v1/rpc/market_stats"
        payload = {"p_community": community}
        
        resp = requests.post(url, json=payload, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0]['total_transactions'] > 0:
                stats = data[0]
                
                response = f"**Market Statistics for {community or 'Dubai'}:**\n\n"
                response += f"• Total Transactions: {stats['total_transactions']:,}\n"
                response += f"• Average Price: AED {stats['avg_price']:,.0f}\n"
                response += f"• Median Price: AED {stats['median_price']:,.0f}\n"
                response += f"• Price Range: AED {stats['min_price']:,.0f} - {stats['max_price']:,.0f}\n"
                response += f"• Average Price/SqFt: AED {stats['avg_price_per_sqft']:,.2f}\n"
                response += f"• Total Volume: AED {stats['total_volume']:,.0f}"
                
                return {
                    "intent": "market_stats",
                    "data": stats,
                    "response": response,
                    "metadata": {"community": community}
                }
        
        return {
            "intent": "market_stats",
            "data": None,
            "response": "No market data available for that community.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_comparables(self, query: str, user_id: str) -> Dict:
        """Handle: 'Find comparable sales for 2-bed 1800 sqft in Serenia'"""
        community = self._extract_community(query)
        bedrooms = self._extract_bedrooms(query)
        size = self._extract_size(query)
        
        if community:
            community = resolve_community_alias(community)
        
        # Use find_comparables RPC
        url = f"{NEON_REST_URL}/rest/v1/rpc/find_comparables"
        payload = {
            "p_community": community,
            "p_bedrooms": bedrooms,
            "p_size_sqft": size,
            "p_months_back": 12,
            "p_limit": 10
        }
        
        resp = requests.post(url, json=payload, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                response = f"Found {len(data)} comparable sales in {community}:\n\n"
                
                for i, comp in enumerate(data, 1):
                    response += f"{i}. {comp['building']}, Unit {comp['unit']}: AED {comp['price']:,.0f}"
                    response += f" ({comp['size_sqft']:.0f} sqft, AED {comp['price_per_sqft']:,.0f}/sqft)"
                    response += f" - {comp['transaction_date']}\n"
                
                avg_psf = sum(c['price_per_sqft'] for c in data) / len(data)
                response += f"\n**Average Price/SqFt:** AED {avg_psf:,.2f}"
                
                if size:
                    estimated_value = avg_psf * size
                    response += f"\n**Estimated Value ({size:.0f} sqft):** AED {estimated_value:,.0f}"
                
                return {
                    "intent": "comparables",
                    "data": data,
                    "response": response,
                    "metadata": {"count": len(data), "avg_psf": avg_psf}
                }
        
        return {
            "intent": "comparables",
            "data": [],
            "response": "No comparable sales found.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_market_trends(self, query: str, user_id: str) -> Dict:
        """Handle: 'How has price changed in Business Bay since 2023?'"""
        community = self._extract_community(query)
        
        if community:
            community = resolve_community_alias(community)
            
            # Use analytics engine
            growth = self.analytics.growth_rate(community, period="YoY")
            
            if "error" not in growth:
                response = f"**Price Trends for {community}:**\n\n"
                
                for period_data in growth['periods'][-5:]:
                    response += f"• {period_data['period']}: AED {period_data['avg_psf']:,.2f}/sqft"
                    if period_data.get('pct_change'):
                        response += f" ({period_data['pct_change']:+.1f}%)"
                    response += f" ({period_data['count']} transactions)\n"
                
                response += f"\n**Cumulative Change:** {growth['cumulative_change']:+.1f}%"
                
                return {
                    "intent": "market_trends",
                    "data": growth,
                    "response": response,
                    "metadata": {"community": community}
                }
        
        return {
            "intent": "market_trends",
            "data": None,
            "response": "Unable to calculate trends for that community.",
            "metadata": {"error": "insufficient_data"}
        }
    
    def _handle_top_investors(self, query: str, user_id: str) -> Dict:
        """Handle: 'Who owns the most properties in City Walk?'"""
        community = self._extract_community(query)
        
        if community:
            community = resolve_community_alias(community)
        
        # Use top_investors RPC
        url = f"{NEON_REST_URL}/rest/v1/rpc/top_investors"
        payload = {
            "p_community": community,
            "p_limit": 10,
            "p_min_properties": 2
        }
        
        resp = requests.post(url, json=payload, headers=HEADERS)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                response = f"**Top Investors in {community or 'Dubai'}:**\n\n"
                
                for i, investor in enumerate(data, 1):
                    response += f"{i}. **{investor['owner_name']}**"
                    if investor.get('owner_phone'):
                        response += f" (📞 {investor['owner_phone']})"
                    response += f"\n   • {investor['total_properties']} properties"
                    if investor.get('portfolio_value'):
                        response += f", AED {investor['portfolio_value']:,.0f} total value"
                    response += "\n"
                
                return {
                    "intent": "top_investors",
                    "data": data,
                    "response": response,
                    "metadata": {"count": len(data)}
                }
        
        return {
            "intent": "top_investors",
            "data": [],
            "response": "No investors found.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_likely_sellers(self, query: str, user_id: str) -> Dict:
        """Handle: 'Find owners who bought 4+ years ago in Orla'"""
        community = self._extract_community(query)
        years = self._extract_years(query)
        
        if community:
            community = resolve_community_alias(community)
        
        # Use analytics engine
        sellers = self.analytics.likely_sellers(
            community=community,
            min_hold_years=years or 3
        )
        
        if sellers:
            response = f"**Likely Sellers in {community or 'Dubai'}** (held {years or 3}+ years):\n\n"
            
            for i, seller in enumerate(sellers[:10], 1):
                response += f"{i}. **{seller['raw_name']}**"
                if seller.get('raw_phone'):
                    response += f" (📞 {seller['raw_phone']})"
                response += f"\n   • {seller['community']}, {seller['building']}, Unit {seller['unit']}"
                response += f"\n   • Held for {seller['hold_years']:.1f} years"
                if seller.get('last_price'):
                    response += f", Last price: AED {seller['last_price']:,.0f}"
                response += "\n"
            
            return {
                "intent": "likely_sellers",
                "data": sellers,
                "response": response,
                "metadata": {"count": len(sellers)}
            }
        
        return {
            "intent": "likely_sellers",
            "data": [],
            "response": "No likely sellers found matching those criteria.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_transaction_velocity(self, query: str, user_id: str) -> Dict:
        """Handle: 'What's the transaction velocity in Serenia?'"""
        community = self._extract_community(query)
        
        if community:
            community = resolve_community_alias(community)
            
            velocity = self.analytics.transaction_velocity(community, window_days=90)
            
            if "error" not in velocity:
                response = f"**Transaction Velocity for {community}:**\n\n"
                response += f"• Transactions per day: {velocity['avg_per_day']:.2f}\n"
                response += f"• Transactions per week: {velocity['avg_per_week']:.1f}\n"
                response += f"• Transactions per month: {velocity['avg_per_month']:.0f}\n"
                response += f"• Recent transactions (90 days): {velocity['recent_transactions']}"
                
                return {
                    "intent": "transaction_velocity",
                    "data": velocity,
                    "response": response,
                    "metadata": {"community": community}
                }
        
        return {
            "intent": "transaction_velocity",
            "data": None,
            "response": "Unable to calculate velocity for that community.",
            "metadata": {"error": "insufficient_data"}
        }
    
    def _handle_community_comparison(self, query: str, user_id: str) -> Dict:
        """Handle: 'Compare Orla vs Serenia for price per sqft'"""
        communities = self._extract_communities(query)
        
        if len(communities) < 2:
            return {
                "intent": "community_comparison",
                "data": None,
                "response": "Please specify at least two communities to compare.",
                "metadata": {"error": "insufficient_input"}
            }
        
        # Resolve aliases
        communities = [resolve_community_alias(c) for c in communities]
        
        # Get stats for each
        comparison_data = []
        for community in communities:
            url = f"{NEON_REST_URL}/rest/v1/rpc/market_stats"
            payload = {"p_community": community}
            resp = requests.post(url, json=payload, headers=HEADERS)
            
            if resp.status_code == 200:
                data = resp.json()
                if data and data[0]['total_transactions'] > 0:
                    comparison_data.append({
                        "community": community,
                        **data[0]
                    })
        
        if comparison_data:
            response = "**Community Comparison:**\n\n"
            
            for comp in comparison_data:
                response += f"**{comp['community']}:**\n"
                response += f"  • Avg Price/SqFt: AED {comp['avg_price_per_sqft']:,.2f}\n"
                response += f"  • Avg Price: AED {comp['avg_price']:,.0f}\n"
                response += f"  • Transactions: {comp['total_transactions']:,}\n\n"
            
            # Winner
            best = max(comparison_data, key=lambda x: x['avg_price_per_sqft'])
            response += f"**Highest Price/SqFt:** {best['community']} at AED {best['avg_price_per_sqft']:,.2f}"
            
            return {
                "intent": "community_comparison",
                "data": comparison_data,
                "response": response,
                "metadata": {"communities": communities}
            }
        
        return {
            "intent": "community_comparison",
            "data": [],
            "response": "Unable to compare those communities.",
            "metadata": {"error": "not_found"}
        }
    
    def _handle_owner_discovery(self, query: str, user_id: str) -> Dict:
        """Handle: 'List owners of 3-bed apartments in City Walk under 2M'"""
        # Similar to property_finder but returns owner details
        return self._handle_property_finder(query, user_id)
    
    def _handle_learning(self, query: str, user_id: str) -> Dict:
        """Handle: 'Explain what transaction velocity means'"""
        query_lower = query.lower()
        
        explanations = {
            "transaction velocity": "Transaction velocity measures how frequently properties change hands in a market. High velocity indicates active buying/selling, while low velocity suggests owners are holding long-term. It's calculated as transactions per unit of time (e.g., per month).",
            
            "price per sqft": "Price per square foot (PSF) is the cost divided by the property size. It normalizes prices across different sizes, making it easier to compare value. Higher PSF usually indicates premium locations or finishes.",
            
            "roi": "Return on Investment (ROI) measures the profit from a property relative to its cost. ROI = (Current Value - Purchase Price) / Purchase Price × 100%. Rental yield is annual rent / property value.",
            
            "appreciation": "Appreciation is the increase in property value over time. It's typically measured year-over-year (YoY) or since purchase. Dubai's high-growth areas can see 10-30% annual appreciation.",
            
            "comparable sales": "Comparable sales (comps) are recent transactions of similar properties used to estimate market value. Agents look at size, bedrooms, location, and transaction date to find the best matches.",
        }
        
        for term, explanation in explanations.items():
            if term in query_lower:
                return {
                    "intent": "learning",
                    "data": {"term": term, "explanation": explanation},
                    "response": f"**{term.title()}:**\n\n{explanation}",
                    "metadata": {"educational": True}
                }
        
        return {
            "intent": "learning",
            "data": None,
            "response": "I can explain: transaction velocity, price per sqft, ROI, appreciation, comparable sales. What would you like to learn about?",
            "metadata": {"suggestions": list(explanations.keys())}
        }
    
    # ========== EXTRACTION HELPERS ==========
    
    def _extract_community(self, query: str) -> Optional[str]:
        """Extract community name from query"""
        # Known communities
        communities = [
            "Business Bay", "Dubai Marina", "Palm Jumeirah", "Downtown Dubai",
            "Burj Khalifa", "City Walk", "Orla", "Serenia", "Six Senses",
            "Muraba", "JVC", "Jumeirah Village Circle"
        ]
        
        query_lower = query.lower()
        for community in communities:
            if community.lower() in query_lower:
                return community
        
        return None
    
    def _extract_communities(self, query: str) -> List[str]:
        """Extract multiple community names from query"""
        communities = []
        
        # Split on "vs", "versus", "and", "or"
        parts = re.split(r'\s+(?:vs\.?|versus|and|or)\s+', query, flags=re.IGNORECASE)
        
        for part in parts:
            community = self._extract_community(part)
            if community and community not in communities:
                communities.append(community)
        
        return communities
    
    def _extract_unit(self, query: str) -> Optional[str]:
        """Extract unit number from query"""
        # Look for patterns like "unit 504", "504", "#504"
        match = re.search(r'(?:unit\s+)?#?(\d+[A-Z]?)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_bedrooms(self, query: str) -> Optional[int]:
        """Extract bedroom count from query"""
        match = re.search(r'(\d+)[- ]?(?:bed|bedroom|br)', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def _extract_size(self, query: str) -> Optional[float]:
        """Extract single size value from query"""
        match = re.search(r'(\d+(?:,\d{3})*)\s*(?:sqft|sq\.?\s*ft\.?)', query, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
        return None
    
    def _extract_size_range(self, query: str) -> Optional[Tuple[float, float]]:
        """Extract size range from query"""
        match = re.search(r'(\d+(?:,\d{3})*)\s*(?:to|-|and)\s*(\d+(?:,\d{3})*)\s*(?:sqft|sq\.?\s*ft\.?)', query, re.IGNORECASE)
        if match:
            min_size = float(match.group(1).replace(',', ''))
            max_size = float(match.group(2).replace(',', ''))
            return (min_size, max_size)
        return None
    
    def _extract_owner_name(self, query: str) -> Optional[str]:
        """Extract owner name from query"""
        # Look for names after "does", "owned by", "portfolio of"
        patterns = [
            r'(?:does|portfolio of|owned by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s+own)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_phone(self, query: str) -> Optional[str]:
        """Extract phone number from query"""
        match = re.search(r'(\+?\d[\d\s\-()]{8,})', query)
        if match:
            return match.group(1)
        return None
    
    def _extract_years(self, query: str) -> Optional[int]:
        """Extract year duration from query"""
        match = re.search(r'(\d+)\s*(?:\+)?\s*years?', query, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None


# Example usage
if __name__ == "__main__":
    ai = RealEstateAI()
    
    test_queries = [
        "Who owns unit 504 in Business Bay?",
        "What's the average price in Downtown Dubai?",
        "Find 2-bed apartments between 1500 and 1900 sqft in City Walk",
        "Show me top investors in Dubai Marina",
        "Compare Business Bay vs Palm Jumeirah for price per sqft",
        "Explain what transaction velocity means",
    ]
    
    print("=" * 80)
    print("DUBAI REAL ESTATE AI - TEST")
    print("=" * 80)
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        print("-" * 80)
        
        result = ai.process_query(query, user_id="test_agent")
        
        print(f"🎯 Intent: {result['intent']}")
        print(f"💬 Response:\n{result['response']}")
        print()
