"""
Analytics Engine: The "Brain" of the Thinking Market Engine

Provides statistical, temporal, and market intelligence functions.
Uses DuckDB for fast in-memory analytics on Supabase data.

Skills:
- Statistical reasoning (avg, median, percentiles, growth rates)
- Temporal pattern recognition (trends, seasonality, YoY)
- Ownership analysis (portfolios, concentration, diversity)
- Comparable analysis (comps engine with regression)
- Market correlation (community price movements)
- Prospecting intelligence (likely sellers, hold duration)
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import duckdb
import pandas as pd
from scipy import stats
from backend.neon_client import select
from backend.utils.phone_utils import normalize_phone

class AnalyticsEngine:
    """Market intelligence and analytical compute engine."""
    
    def __init__(self):
        self.db = duckdb.connect(":memory:")
        self._cache = {}

    def _fetch_page(
        self,
        table: str,
        select_fields: str,
        filters: Optional[Dict] = None,
        limit: int = 1000,
        offset: int = 0,
        order: Optional[str] = None,
        max_retries: int = 3
    ) -> List[Dict]:
        for attempt in range(max_retries):
            try:
                return asyncio.run(
                    select(
                        table,
                        select_fields=select_fields,
                        filters=filters,
                        limit=limit,
                        offset=offset,
                        order=order
                    )
                )
            except Exception as exc:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                time.sleep(wait_time)
        return []
    
    def fetch_transactions(self, filters: Optional[Dict] = None, max_retries: int = 3) -> pd.DataFrame:
        """Fetch transactions from Supabase with pagination and retry logic."""
        all_data = []
        offset = 0
        page_size = 1000

        while True:
            page_data = self._fetch_page(
                "transactions",
                "community,building,unit,property_type,size_sqft,price,transaction_date,buyer_name,seller_name,buyer_phone,seller_phone,bedrooms",
                filters=filters,
                limit=page_size,
                offset=offset,
                order="transaction_date.desc",
                max_retries=max_retries
            )

            if not page_data:
                break

            all_data.extend(page_data)

            if len(page_data) < page_size:
                break

            offset += page_size

        df = pd.DataFrame(all_data)
        if not df.empty and "transaction_date" in df.columns:
            df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        return df

    def fetch_owners(self, max_retries: int = 3) -> pd.DataFrame:
        """Fetch owners with cluster info (paginated)."""
        all_data = []
        offset = 0
        page_size = 1000

        while True:
            page_data = self._fetch_page(
                "owners",
                "id,raw_name,raw_phone,norm_name,norm_phone,cluster_id",
                limit=page_size,
                offset=offset,
                max_retries=max_retries
            )

            if not page_data:
                break

            all_data.extend(page_data)

            if len(page_data) < page_size:
                break

            offset += page_size

        return pd.DataFrame(all_data)

    def fetch_properties(self, max_retries: int = 3) -> pd.DataFrame:
        """Fetch properties (paginated)."""
        all_data = []
        offset = 0
        page_size = 1000

        while True:
            page_data = self._fetch_page(
                "properties",
                "*",
                limit=page_size,
                offset=offset,
                max_retries=max_retries
            )

            if not page_data:
                break

            all_data.extend(page_data)

            if len(page_data) < page_size:
                break

            offset += page_size

        return pd.DataFrame(all_data)
    
    # ========== SKILL 1: STATISTICAL REASONING ==========
    
    def market_stats(self, community: Optional[str] = None, 
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> Dict:
        """
        Calculate market statistics.
        
        Returns:
            avg_price, median_price, avg_psf, total_volume, transaction_count
        """
        filters = {}
        if community:
            filters["community"] = f"ilike.%{community}%"
        # Use proper Supabase filter syntax for date ranges
        if start_date and end_date:
            filters["transaction_date"] = f"gte.{start_date}&transaction_date=lte.{end_date}"
        elif start_date:
            filters["transaction_date"] = f"gte.{start_date}"
        elif end_date:
            filters["transaction_date"] = f"lte.{end_date}"
        
        df = self.fetch_transactions(filters)
        
        if df.empty:
            return {"error": "No data found"}
        
        # Data quality filters: remove noise and errors
        df = df[df['price'] > 0]
        df = df[df['size_sqft'] >= 1076]  # Minimum realistic size (100 sqm = 1,076 sqft)
        
        # Calculate price per sqft
        df['psf'] = df['price'] / df['size_sqft']
        df = df[df['psf'].notna() & (df['psf'] > 0)]
        
        return {
            "avg_price": float(df['price'].mean()),
            "median_price": float(df['price'].median()),
            "avg_psf": float(df['psf'].mean()),
            "median_psf": float(df['psf'].median()),
            "total_volume": float(df['price'].sum()),
            "transaction_count": len(df),
            "percentile_25": float(df['price'].quantile(0.25)),
            "percentile_75": float(df['price'].quantile(0.75)),
        }
    
    def growth_rate(self, community: str, period: str = "YoY") -> Dict:
        """
        Calculate price growth rate.
        
        Args:
            period: "YoY" (year-over-year), "QoQ" (quarter), "MoM" (month)
        """
        df = self.fetch_transactions({"community": f"ilike.%{community}%"})
        
        if df.empty:
            return {"error": "No data found"}
        
        # Data quality filters
        df = df[df['price'] > 0]
        df = df[df['size_sqft'] >= 1076]  # 100 sqm = 1,076 sqft
        
        df['psf'] = df['price'] / df['size_sqft']
        df = df[df['psf'].notna() & (df['psf'] > 0)]
        
        # Group by time period
        if period == "YoY":
            df['period'] = df['transaction_date'].dt.year
        elif period == "QoQ":
            df['period'] = df['transaction_date'].dt.to_period('Q').astype(str)  # Convert to string
        else:  # MoM
            df['period'] = df['transaction_date'].dt.to_period('M').astype(str)  # Convert to string
        
        stats = df.groupby('period')['psf'].agg(['mean', 'count']).reset_index()
        stats.columns = ['period', 'avg_psf', 'count']
        stats['pct_change'] = stats['avg_psf'].pct_change() * 100
        
        return {
            "periods": stats.to_dict('records'),
            "latest_change": float(stats['pct_change'].iloc[-1]) if len(stats) > 1 else 0,
            "cumulative_change": float((stats['avg_psf'].iloc[-1] / stats['avg_psf'].iloc[0] - 1) * 100) if len(stats) > 1 else 0
        }
    
    # ========== SKILL 2: TEMPORAL PATTERN RECOGNITION ==========
    
    def seasonal_patterns(self, community: Optional[str] = None) -> Dict:
        """Detect seasonal patterns in transaction activity."""
        filters = {}
        if community:
            filters["community"] = f"ilike.%{community}%"
        
        df = self.fetch_transactions(filters)
        
        if df.empty:
            return {"error": "No data found"}
        
        df['month'] = df['transaction_date'].dt.month
        df['month_name'] = df['transaction_date'].dt.month_name()
        
        monthly = df.groupby(['month', 'month_name']).agg({
            'price': ['count', 'sum', 'mean']
        }).reset_index()
        
        monthly.columns = ['month', 'month_name', 'transaction_count', 'total_volume', 'avg_price']
        monthly = monthly.sort_values('transaction_count', ascending=False)
        
        return {
            "busiest_months": monthly.head(3).to_dict('records'),
            "slowest_months": monthly.tail(3).to_dict('records'),
            "monthly_breakdown": monthly.to_dict('records')
        }
    
    def transaction_velocity(self, community: str, window_days: int = 90) -> Dict:
        """Calculate transaction velocity (sales per day)."""
        df = self.fetch_transactions({"community": f"ilike.%{community}%"})
        
        if df.empty:
            return {"error": "No data found"}
        
        df = df.sort_values('transaction_date')
        cutoff = df['transaction_date'].max() - timedelta(days=window_days)
        recent = df[df['transaction_date'] >= cutoff]
        
        velocity = len(recent) / window_days
        
        return {
            "velocity": float(velocity),
            "window_days": window_days,
            "recent_transactions": len(recent),
            "avg_per_day": float(velocity),
            "avg_per_week": float(velocity * 7),
            "avg_per_month": float(velocity * 30)
        }
    
    # ========== SKILL 3: OWNERSHIP NETWORK ANALYSIS ==========
    
    def top_investors(self, limit: int = 10) -> List[Dict]:
        """Identify top investors by portfolio value and diversity."""
        props = self.fetch_properties()
        owners = self.fetch_owners()
        
        if props.empty or owners.empty:
            return []
        
        # Merge to get owner info
        merged = props.merge(owners, left_on='owner_id', right_on='id')
        
        # Group by cluster to consolidate same investor
        investor_stats = merged.groupby('cluster_id').agg({
            'id_x': 'count',  # property count
            'last_price': 'sum',  # total portfolio value
            'community': lambda x: x.nunique(),  # community diversity
            'raw_name': 'first',
            'raw_phone': 'first'
        }).reset_index()
        
        investor_stats.columns = ['cluster_id', 'property_count', 'portfolio_value', 
                                  'community_diversity', 'name', 'phone']
        
        investor_stats = investor_stats.sort_values('portfolio_value', ascending=False)
        
        return investor_stats.head(limit).to_dict('records')
    
    def owner_portfolio(self, owner_phone: str) -> Dict:
        """Get complete portfolio for an owner (using normalized phone)."""
        props = self.fetch_properties()
        owners = self.fetch_owners()
        
        # Normalize input phone
        norm_phone = normalize_phone(owner_phone)
        
        # Find owner by normalized phone
        owner = owners[owners['norm_phone'] == norm_phone]
        
        # Fallback to raw phone if not found
        if owner.empty:
            owner = owners[owners['raw_phone'] == owner_phone]
        
        if owner.empty:
            return {"error": "Owner not found"}
        
        cluster_id = owner.iloc[0].get('cluster_id')
        
        # Get all properties in this cluster (if cluster exists)
        if cluster_id and pd.notna(cluster_id):
            owner_props = props[props['owner_id'].isin(owners[owners['cluster_id'] == cluster_id]['id'])]
        else:
            # No cluster, just use owner_id
            owner_props = props[props['owner_id'] == owner.iloc[0]['id']]
        
        return {
            "owner_name": owner.iloc[0]['raw_name'],
            "owner_phone": owner.iloc[0]['raw_phone'],
            "cluster_id": cluster_id,
            "property_count": len(owner_props),
            "total_value": float(owner_props['last_price'].sum()),
            "communities": owner_props['community'].unique().tolist(),
            "properties": owner_props[['community', 'building', 'unit', 'last_price', 'last_transaction_date']].to_dict('records')
        }
    
    # ========== SKILL 4: COMPARABLE ANALYSIS (COMPS ENGINE) ==========
    
    def find_comparables(self, community: str, building: Optional[str] = None,
                        size_sqft: Optional[float] = None, 
                        bedrooms: Optional[int] = None,
                        months_back: int = 18) -> List[Dict]:
        """Find comparable recent sales."""
        filters = {
            "community": f"ilike.%{community}%",
            "transaction_date": f"gte.{(datetime.now() - timedelta(days=months_back*30)).date()}"
        }
        
        df = self.fetch_transactions(filters)
        
        if df.empty:
            return []
        
        # Calculate similarity score
        if size_sqft:
            df['size_diff'] = abs(df['size_sqft'] - size_sqft) / size_sqft
            df = df[df['size_diff'] < 0.3]  # Within 30% size range
        
        if building:
            df = df[df['building'].str.contains(building, case=False, na=False)]
        
        df = df.sort_values('transaction_date', ascending=False)
        
        return df.head(20)[['community', 'building', 'unit', 'size_sqft', 
                            'price', 'transaction_date']].to_dict('records')
    
    def estimate_value(self, community: str, size_sqft: float, 
                      building: Optional[str] = None) -> Dict:
        """Estimate property value using comparable sales regression."""
        comps = self.find_comparables(community, building, size_sqft)
        
        if len(comps) < 3:
            return {"error": "Insufficient comparable sales"}
        
        df = pd.DataFrame(comps)
        df = df[df['price'].notna() & df['size_sqft'].notna()]
        
        if len(df) < 3:
            return {"error": "Insufficient valid comparables"}
        
        # Simple linear regression: price ~ size_sqft
        slope, intercept, r_value, p_value, std_err = stats.linregress(df['size_sqft'], df['price'])
        
        estimated_price = slope * size_sqft + intercept
        confidence = r_value ** 2  # R-squared
        
        return {
            "estimated_price": float(estimated_price),
            "confidence": float(confidence),
            "comparable_count": len(comps),
            "avg_psf": float(df['price'].sum() / df['size_sqft'].sum()),
            "price_range": {
                "min": float(df['price'].min()),
                "max": float(df['price'].max()),
                "median": float(df['price'].median())
            }
        }
    
    # ========== SKILL 5: MARKET CORRELATION ==========
    
    def community_correlation(self, communities: List[str]) -> Dict:
        """Calculate price correlation between communities."""
        all_data = []
        
        for community in communities:
            df = self.fetch_transactions({"community": f"ilike.%{community}%"})
            if not df.empty:
                # Data quality filters
                df = df[df['price'] > 0]
                df = df[df['size_sqft'] >= 1076]  # 100 sqm = 1,076 sqft
                df['psf'] = df['price'] / df['size_sqft']
                df = df[df['psf'].notna() & (df['psf'] > 0)]
                df['month'] = df['transaction_date'].dt.to_period('M').astype(str)
                monthly = df.groupby('month')['psf'].mean().reset_index()
                monthly['community'] = community
                all_data.append(monthly)
        
        if len(all_data) < 2:
            return {"error": "Need at least 2 communities with data"}
        
        combined = pd.concat(all_data)
        pivot = combined.pivot(index='month', columns='community', values='psf')
        
        # Drop months with NaNs to avoid spurious correlations
        pivot_clean = pivot.dropna()
        overlapping_months = len(pivot_clean)
        
        if overlapping_months < 3:
            return {"error": f"Insufficient overlapping data points ({overlapping_months} months)"}
        
        corr_matrix = pivot_clean.corr()
        
        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "strongest_correlations": self._find_strongest_correlations(corr_matrix, overlapping_months),
            "overlapping_months": overlapping_months
        }
    
    def _find_strongest_correlations(self, corr_matrix: pd.DataFrame, overlapping_months: int) -> List[Dict]:
        """Extract strongest correlations from matrix."""
        correlations = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                correlations.append({
                    "community_1": corr_matrix.columns[i],
                    "community_2": corr_matrix.columns[j],
                    "correlation": float(corr_matrix.iloc[i, j]),
                    "data_points": overlapping_months
                })
        
        return sorted(correlations, key=lambda x: abs(x['correlation']), reverse=True)[:5]
    
    # ========== SKILL 6: PROSPECTING INTELLIGENCE ==========
    
    def likely_sellers(self, community: Optional[str] = None, 
                      min_hold_years: int = 3,
                      min_appreciation: float = 0.15) -> List[Dict]:
        """Identify owners likely to sell based on hold duration and appreciation."""
        props = self.fetch_properties()
        owners = self.fetch_owners()
        
        if props.empty or owners.empty:
            return []
        
        # Filter by community
        if community:
            props = props[props['community'].str.contains(community, case=False, na=False)]
        
        # Guard against null dates
        props = props[props['last_transaction_date'].notna()]
        
        if props.empty:
            return []
        
        # Calculate hold duration (using Dubai timezone-aware datetime)
        props['last_transaction_date'] = pd.to_datetime(props['last_transaction_date'])
        # Use timezone-naive comparison (dates are stored as dates, not datetimes)
        now = pd.Timestamp.now().normalize()  # Normalize to date
        props['hold_years'] = (now - props['last_transaction_date']).dt.days / 365.25
        
        # Filter by criteria - only properties with valid hold duration
        candidates = props[(props['hold_years'] >= min_hold_years) & (props['hold_years'].notna())]
        
        if candidates.empty:
            return []
        
        # Merge with owner info
        merged = candidates.merge(owners, left_on='owner_id', right_on='id', suffixes=('_prop', '_owner'))
        
        # Round hold_years for readability
        merged['hold_years'] = merged['hold_years'].round(1)
        
        return merged[['raw_name', 'raw_phone', 'community', 'building', 'unit', 
                      'last_price', 'hold_years']].head(50).to_dict('records')
    
    def market_activity_score(self, community: str) -> Dict:
        """Calculate market activity score (0-100) based on velocity, volume, and trend."""
        # Get recent transactions
        df = self.fetch_transactions({"community": f"ilike.%{community}%"})
        
        if df.empty:
            return {"score": 0, "factors": {}}
        
        # Velocity score (transactions per month)
        recent_90d = df[df['transaction_date'] >= (datetime.now() - timedelta(days=90))]
        velocity = len(recent_90d) / 3  # per month
        velocity_score = min(velocity / 10 * 100, 100)  # Normalize to 100
        
        # Volume score (total value)
        total_volume = df['price'].sum()
        volume_score = min((total_volume / 1e9) * 100, 100)  # Normalize to 100
        
        # Trend score (recent vs historical)
        df['month'] = df['transaction_date'].dt.to_period('M').astype(str)
        monthly = df.groupby('month')['price'].count()
        if len(monthly) > 1:
            trend = (monthly.iloc[-1] / monthly.mean() - 1) * 100
            trend_score = max(0, min(50 + trend, 100))
        else:
            trend_score = 50
        
        # Weighted composite score
        composite = (velocity_score * 0.4 + volume_score * 0.3 + trend_score * 0.3)
        
        return {
            "score": float(composite),
            "factors": {
                "velocity_score": float(velocity_score),
                "volume_score": float(volume_score),
                "trend_score": float(trend_score),
                "velocity_per_month": float(velocity),
                "total_volume": float(total_volume)
            }
        }


# Example usage
if __name__ == "__main__":
    engine = AnalyticsEngine()
    
    print("🧠 Analytics Engine Ready\n")
    
    # Test market stats
    print("=== Market Stats for Business Bay ===")
    stats = engine.market_stats("Business Bay")
    print(f"Avg Price: AED {stats['avg_price']:,.0f}")
    print(f"Avg PSF: AED {stats['avg_psf']:,.0f}")
    print(f"Total Transactions: {stats['transaction_count']}")
    
    print("\n=== Top Investors ===")
    investors = engine.top_investors(5)
    for i, inv in enumerate(investors, 1):
        print(f"{i}. {inv['name']} - AED {inv['portfolio_value']:,.0f} ({inv['property_count']} properties)")
    
    print("\n✅ Engine operational!")
