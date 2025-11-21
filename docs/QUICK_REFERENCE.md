# Quick Reference Guide - Dubai Real Estate Engine

## 🚀 1-Minute Setup

```bash
# Check environment variables
echo $env:SUPABASE_URL
echo $env:SUPABASE_SERVICE_ROLE_KEY

# Apply RPC functions (one-time setup)
# Open: https://supabase.com/dashboard/project/ggevgecnnmcznurxhplu/sql/new
# Copy/paste contents of: supabase_rpc_functions.sql
# Click RUN

# Verify
python test_rpc_functions.py
```

---

## 📊 Common Tasks

### Generate CMA Report
```python
from cma_report_generator import CMAReportGenerator

cma = CMAReportGenerator("Business Bay", property_type="Apartment", bedrooms=2, size_sqft=1000)
cma.fetch_data()
cma.generate_pdf("report.pdf")
cma.generate_csv("comparables.csv")
```

### Export Top Investors
```python
from cma_report_generator import generate_investor_list_csv

generate_investor_list_csv(community="Dubai Marina", min_properties=5, output_path="investors.csv")
```

### Export Owner Portfolio
```python
from cma_report_generator import generate_owner_portfolio_csv

generate_owner_portfolio_csv(owner_name="EMAAR", output_path="emaar_portfolio.csv")
```

### AI Chat (Natural Language)
```python
from thinking_engine_orchestrator import ThinkingEngine

engine = ThinkingEngine(use_ai=True)
print(engine.chat("What are average prices in Business Bay?"))
print(engine.chat("Show me top 10 investors in JVC"))
print(engine.chat("Generate a CMA report for 2BR in Dubai Marina"))
```

### Manual Analytics (Python)
```python
from analytics_engine import DubaiRealEstateAnalytics

engine = DubaiRealEstateAnalytics()

# Market stats
stats = engine.market_stats(community="Business Bay", bedrooms=2)

# Top investors
investors = engine.top_investors(limit=10)

# Comparables
comps = engine.find_comparables("Business Bay", bedrooms=2, size_sqft=1000)

# Seasonal patterns
patterns = engine.seasonal_patterns("Business Bay")

# Likely sellers (prospecting)
sellers = engine.likely_sellers("Dubai Marina", min_years=3)
```

---

## 🔍 Quick Queries (SQL)

Copy/paste into Supabase SQL Editor:

### Top 10 Communities by Transaction Volume
```sql
SELECT community, COUNT(*) as transactions, ROUND(AVG(price), 0) as avg_price
FROM transactions
WHERE price > 0
GROUP BY community
ORDER BY transactions DESC
LIMIT 10;
```

### Biggest Investors
```sql
SELECT buyer_name, buyer_phone, COUNT(*) as properties, SUM(price) as total_spent
FROM transactions
WHERE buyer_name IS NOT NULL
GROUP BY buyer_name, buyer_phone
HAVING COUNT(*) >= 5
ORDER BY properties DESC
LIMIT 20;
```

### Price Trends (Last 12 Months)
```sql
SELECT 
    TO_CHAR(transaction_date, 'YYYY-MM') as month,
    COUNT(*) as transactions,
    ROUND(AVG(price), 0) as avg_price
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '12 months'
  AND price > 0
GROUP BY month
ORDER BY month DESC;
```

### Properties by Owner
```sql
SELECT o.norm_name, o.norm_phone, p.community, p.building, p.unit, p.last_price
FROM owners o
JOIN properties p ON p.owner_id = o.id
WHERE o.norm_name ILIKE '%EMAAR%'
ORDER BY p.last_price DESC;
```

---

## 🎯 RPC Function Examples

### Via Python
```python
import requests
import os

url = f"{os.getenv('SUPABASE_URL')}/rest/v1/rpc/market_stats"
headers = {
    "apikey": os.getenv('SUPABASE_SERVICE_ROLE_KEY'),
    "Authorization": f"Bearer {os.getenv('SUPABASE_SERVICE_ROLE_KEY')}",
    "Content-Type": "application/json"
}
params = {"p_community": "Business Bay", "p_bedrooms": 2}
response = requests.post(url, headers=headers, json=params)
print(response.json())
```

### All Available RPC Functions
1. `market_stats(community, property_type, bedrooms, start_date, end_date)`
2. `top_investors(community, limit, min_properties)`
3. `owner_portfolio(owner_name, owner_phone)`
4. `find_comparables(community, property_type, bedrooms, size_sqft, months_back, limit)`
5. `transaction_velocity(community, months)`
6. `seasonal_patterns(community)`
7. `likely_sellers(community, min_years_owned, limit)`
8. `compare_communities(communities[])`
9. `property_history(community, building, unit)`
10. `search_owners(query, limit)`

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `cma_report_generator.py` | Generate PDF/CSV reports |
| `thinking_engine_orchestrator.py` | AI chat interface |
| `analytics_engine.py` | Python analytics library |
| `test_rpc_functions.py` | Test RPC functions |
| `validate_data.py` | Verify database integrity |
| `SYSTEM_COMPLETE.md` | Full documentation |
| `supabase_rpc_functions.sql` | PostgreSQL functions (apply once) |

---

## 🔧 Troubleshooting One-Liners

```bash
# Validate database
python validate_data.py

# Test RPC functions
python test_rpc_functions.py

# Check environment
echo $env:SUPABASE_URL
echo $env:SUPABASE_SERVICE_ROLE_KEY
echo $env:OPENAI_API_KEY

# Reinstall dependencies
pip install --upgrade pandas openpyxl requests rapidfuzz duckdb scipy psycopg2-binary reportlab matplotlib pillow openai
```

---

## 💡 Pro Tips

1. **Batch Operations**: Use `generate_investor_list_csv()` to export lists of 100+ investors at once
2. **Date Filters**: Use RPC `market_stats` with `start_date`/`end_date` for specific time periods
3. **Prospecting**: `likely_sellers()` finds properties held 3+ years (great for lead generation)
4. **CMA Accuracy**: Provide `size_sqft` parameter for more accurate comparable matching
5. **Performance**: RPC functions are faster than Python analytics for simple queries

---

## 📞 Most Common Questions

**Q: How do I apply RPC functions?**  
A: Open Supabase SQL Editor, paste `supabase_rpc_functions.sql`, click RUN

**Q: Can I use this without OpenAI?**  
A: Yes! Use `ThinkingEngine(use_ai=False)` for keyword-based routing

**Q: How do I export data to Excel?**  
A: All CSVs open in Excel. For custom exports, query via SQL and export

**Q: Where is my data stored?**  
A: Supabase PostgreSQL at `https://ggevgecnnmcznurxhplu.supabase.co`

**Q: How do I add more transactions?**  
A: Place Excel files in `.data_raw/` and re-run `ingest_dubai_real_estate.py`

---

## 🎉 Quick Wins

### Generate Reports for All Major Communities
```python
from cma_report_generator import CMAReportGenerator

communities = ["Business Bay", "Dubai Marina", "Downtown Dubai", "JVC", "Dubai Hills"]

for community in communities:
    cma = CMAReportGenerator(community, bedrooms=2)
    cma.fetch_data()
    cma.generate_pdf(f"{community}_2BR_CMA.pdf")
    print(f"✅ {community} report generated")
```

### Bulk Investor Export
```python
from cma_report_generator import generate_investor_list_csv

communities = ["Business Bay", "Dubai Marina", "JVC"]

for community in communities:
    generate_investor_list_csv(community, min_properties=3, output_path=f"Investors_{community}.csv")
```

---

**Need more details? See `SYSTEM_COMPLETE.md` for comprehensive documentation.**
