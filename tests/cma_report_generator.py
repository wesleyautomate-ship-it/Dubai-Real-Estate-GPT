"""
CMA (Comparative Market Analysis) Report Generator
Generates professional PDF and CSV reports with market analysis
"""
import os
import csv
import requests
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

HEADERS = {
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json"
}


class CMAReportGenerator:
    """Generate comprehensive CMA reports"""
    
    def __init__(self, community, property_type=None, bedrooms=None, size_sqft=None):
        self.community = community
        self.property_type = property_type
        self.bedrooms = bedrooms
        self.size_sqft = size_sqft
        self.report_date = datetime.now()
        
        # Data containers
        self.market_stats = None
        self.comparables = []
        self.transaction_history = []
        self.seasonal_data = []
        
    def fetch_data(self):
        """Fetch all required data from Supabase"""
        print(f"Fetching data for {self.community}...")
        
        # 1. Market Statistics
        print("  - Market statistics...")
        stats_url = f"{SUPABASE_URL}/rest/v1/rpc/market_stats"
        stats_params = {
            "p_community": self.community,
            "p_property_type": self.property_type,
            "p_bedrooms": self.bedrooms
        }
        stats_resp = requests.post(stats_url, headers=HEADERS, json=stats_params)
        if stats_resp.status_code == 200:
            data = stats_resp.json()
            self.market_stats = data[0] if data else {}
        
        # 2. Comparable Properties
        print("  - Comparable properties...")
        comps_url = f"{SUPABASE_URL}/rest/v1/rpc/find_comparables"
        comps_params = {
            "p_community": self.community,
            "p_property_type": self.property_type,
            "p_bedrooms": self.bedrooms,
            "p_size_sqft": self.size_sqft,
            "p_months_back": 12,
            "p_limit": 20
        }
        comps_resp = requests.post(comps_url, headers=HEADERS, json=comps_params)
        if comps_resp.status_code == 200:
            self.comparables = comps_resp.json()
        
        # 3. Transaction Velocity
        print("  - Transaction velocity...")
        velocity_url = f"{SUPABASE_URL}/rest/v1/rpc/transaction_velocity"
        velocity_params = {"p_community": self.community, "p_months": 12}
        velocity_resp = requests.post(velocity_url, headers=HEADERS, json=velocity_params)
        if velocity_resp.status_code == 200:
            self.transaction_history = velocity_resp.json()
        
        # 4. Seasonal Patterns
        print("  - Seasonal patterns...")
        seasonal_url = f"{SUPABASE_URL}/rest/v1/rpc/seasonal_patterns"
        seasonal_params = {"p_community": self.community}
        seasonal_resp = requests.post(seasonal_url, headers=HEADERS, json=seasonal_params)
        if seasonal_resp.status_code == 200:
            self.seasonal_data = seasonal_resp.json()
        
        print("✅ Data fetched successfully")
        return True
    
    def generate_charts(self):
        """Generate charts for the report"""
        charts = {}
        
        # Chart 1: Transaction Velocity
        if self.transaction_history:
            plt.figure(figsize=(10, 4))
            months = [t['year_month'] for t in self.transaction_history]
            counts = [t['transaction_count'] for t in self.transaction_history]
            plt.plot(months, counts, marker='o', linewidth=2, markersize=6)
            plt.title(f'Transaction Volume - {self.community}', fontsize=14, fontweight='bold')
            plt.xlabel('Month')
            plt.ylabel('Number of Transactions')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            velocity_chart = 'temp_velocity_chart.png'
            plt.savefig(velocity_chart, dpi=150, bbox_inches='tight')
            plt.close()
            charts['velocity'] = velocity_chart
        
        # Chart 2: Price Distribution
        if self.comparables:
            plt.figure(figsize=(10, 4))
            prices = [c['price'] for c in self.comparables if c.get('price')]
            if prices:
                plt.hist(prices, bins=15, color='#4CAF50', alpha=0.7, edgecolor='black')
                plt.title(f'Price Distribution - {self.community}', fontsize=14, fontweight='bold')
                plt.xlabel('Price (AED)')
                plt.ylabel('Frequency')
                plt.grid(True, alpha=0.3, axis='y')
                plt.tight_layout()
                price_chart = 'temp_price_chart.png'
                plt.savefig(price_chart, dpi=150, bbox_inches='tight')
                plt.close()
                charts['price'] = price_chart
        
        return charts
    
    def generate_pdf(self, output_path="CMA_Report.pdf"):
        """Generate PDF report"""
        print(f"\nGenerating PDF report: {output_path}")
        
        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        title = Paragraph(f"Comparative Market Analysis<br/>{self.community}", title_style)
        elements.append(title)
        
        # Report Info
        report_info = f"<b>Report Date:</b> {self.report_date.strftime('%B %d, %Y')}<br/>"
        if self.property_type:
            report_info += f"<b>Property Type:</b> {self.property_type.title()}<br/>"
        if self.bedrooms:
            report_info += f"<b>Bedrooms:</b> {self.bedrooms}<br/>"
        if self.size_sqft:
            report_info += f"<b>Approximate Size:</b> {self.size_sqft:,.0f} sq ft<br/>"
        
        elements.append(Paragraph(report_info, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Market Statistics
        elements.append(Paragraph("Market Statistics", heading_style))
        
        if self.market_stats:
            stats_data = [
                ['Metric', 'Value'],
                ['Average Price', f"AED {self.market_stats.get('avg_price', 0):,.0f}"],
                ['Median Price', f"AED {self.market_stats.get('median_price', 0):,.0f}"],
                ['Min Price', f"AED {self.market_stats.get('min_price', 0):,.0f}"],
                ['Max Price', f"AED {self.market_stats.get('max_price', 0):,.0f}"],
                ['Total Transactions', f"{self.market_stats.get('total_transactions', 0):,}"],
                ['Total Volume', f"AED {self.market_stats.get('total_volume', 0):,.0f}"],
                ['Avg Price/SqFt', f"AED {self.market_stats.get('avg_price_per_sqft', 0):,.0f}"],
            ]
            
            stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ]))
            elements.append(stats_table)
        
        elements.append(Spacer(1, 20))
        
        # Charts
        charts = self.generate_charts()
        if charts.get('velocity'):
            elements.append(Paragraph("Transaction Volume Trend", heading_style))
            img = Image(charts['velocity'], width=6*inch, height=2.4*inch)
            elements.append(img)
            elements.append(Spacer(1, 10))
        
        if charts.get('price'):
            elements.append(Paragraph("Price Distribution", heading_style))
            img = Image(charts['price'], width=6*inch, height=2.4*inch)
            elements.append(img)
            elements.append(Spacer(1, 10))
        
        # Comparable Properties
        elements.append(PageBreak())
        elements.append(Paragraph("Comparable Properties", heading_style))
        
        if self.comparables:
            # Take top 10 comparables
            comp_data = [['Building', 'Unit', 'Beds', 'Size', 'Price', 'Price/SqFt', 'Date']]
            for comp in self.comparables[:10]:
                comp_data.append([
                    comp.get('building', '')[:20],
                    comp.get('unit', '')[:10],
                    str(comp.get('bedrooms', '')),
                    f"{comp.get('size_sqft', 0):,.0f}",
                    f"{comp.get('price', 0):,.0f}",
                    f"{comp.get('price_per_sqft', 0):,.0f}",
                    comp.get('transaction_date', '')[:10]
                ])
            
            comp_table = Table(comp_data, colWidths=[1.2*inch, 0.8*inch, 0.5*inch, 0.8*inch, 1*inch, 0.9*inch, 0.8*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3f51b5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(comp_table)
        
        # Build PDF
        doc.build(elements)
        
        # Cleanup temp charts
        for chart_path in charts.values():
            if os.path.exists(chart_path):
                os.remove(chart_path)
        
        print(f"✅ PDF report generated: {output_path}")
        return output_path
    
    def generate_csv(self, output_path="CMA_Comparables.csv"):
        """Generate CSV export of comparable properties"""
        print(f"\nGenerating CSV export: {output_path}")
        
        if not self.comparables:
            print("❌ No comparables to export")
            return None
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Community', 'Building', 'Unit', 'Property Type', 'Bedrooms',
                'Size (SqFt)', 'Price (AED)', 'Price per SqFt', 'Transaction Date',
                'Buyer Name', 'Similarity Score'
            ])
            
            # Data
            for comp in self.comparables:
                writer.writerow([
                    comp.get('community', ''),
                    comp.get('building', ''),
                    comp.get('unit', ''),
                    comp.get('property_type', ''),
                    comp.get('bedrooms', ''),
                    comp.get('size_sqft', ''),
                    comp.get('price', ''),
                    comp.get('price_per_sqft', ''),
                    comp.get('transaction_date', ''),
                    comp.get('buyer_name', ''),
                    comp.get('similarity_score', '')
                ])
        
        print(f"✅ CSV export generated: {output_path}")
        return output_path


def generate_investor_list_csv(community=None, min_properties=3, output_path="Top_Investors.csv"):
    """Generate CSV list of top investors with contact info"""
    print(f"\nGenerating investor list: {output_path}")
    
    # Fetch top investors
    url = f"{SUPABASE_URL}/rest/v1/rpc/top_investors"
    params = {
        "p_community": community,
        "p_limit": 100,
        "p_min_properties": min_properties
    }
    
    response = requests.post(url, headers=HEADERS, json=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch investors: {response.status_code}")
        return None
    
    investors = response.json()
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Owner Name', 'Phone Number', 'Total Properties', 
            'Portfolio Value (AED)', 'Avg Property Price (AED)', 'Communities'
        ])
        
        # Data
        for inv in investors:
            communities = ', '.join(inv.get('communities', []))
            writer.writerow([
                inv.get('owner_name', ''),
                inv.get('owner_phone', ''),
                inv.get('total_properties', ''),
                inv.get('portfolio_value', ''),
                inv.get('avg_property_price', ''),
                communities
            ])
    
    print(f"✅ Investor list generated: {output_path} ({len(investors)} investors)")
    return output_path


def generate_owner_portfolio_csv(owner_name=None, owner_phone=None, output_path="Owner_Portfolio.csv"):
    """Generate CSV of specific owner's portfolio"""
    print(f"\nGenerating owner portfolio: {output_path}")
    
    # Fetch owner portfolio
    url = f"{SUPABASE_URL}/rest/v1/rpc/owner_portfolio"
    params = {
        "p_owner_name": owner_name,
        "p_owner_phone": owner_phone
    }
    
    response = requests.post(url, headers=HEADERS, json=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch portfolio: {response.status_code}")
        return None
    
    portfolio = response.json()
    
    if not portfolio:
        print("❌ No properties found for this owner")
        return None
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'Owner Name', 'Phone', 'Community', 'Building', 'Unit', 
            'Property Type', 'Bedrooms', 'Size (SqFt)', 'Last Price (AED)', 
            'Last Transaction Date', 'Total Transactions'
        ])
        
        # Data
        for prop in portfolio:
            writer.writerow([
                prop.get('owner_name', ''),
                prop.get('owner_phone', ''),
                prop.get('property_community', ''),
                prop.get('property_building', ''),
                prop.get('property_unit', ''),
                prop.get('property_type', ''),
                prop.get('bedrooms', ''),
                prop.get('size_sqft', ''),
                prop.get('last_price', ''),
                prop.get('last_transaction_date', ''),
                prop.get('purchase_count', '')
            ])
    
    print(f"✅ Owner portfolio generated: {output_path} ({len(portfolio)} properties)")
    return output_path


# Example usage
if __name__ == "__main__":
    print("="*60)
    print("CMA REPORT GENERATOR - Dubai Real Estate")
    print("="*60)
    
    # Example 1: Generate CMA Report for Business Bay 2BR apartments
    print("\n📊 Example 1: CMA Report for Business Bay")
    cma = CMAReportGenerator(
        community="Business Bay",
        property_type="Apartment",
        bedrooms=2,
        size_sqft=1000
    )
    cma.fetch_data()
    cma.generate_pdf("Business_Bay_2BR_CMA.pdf")
    cma.generate_csv("Business_Bay_2BR_Comparables.csv")
    
    # Example 2: Generate Top Investors List
    print("\n📊 Example 2: Top Investors List")
    generate_investor_list_csv(
        community=None,  # All communities
        min_properties=5,
        output_path="Top_Investors_Dubai.csv"
    )
    
    print("\n✅ All reports generated successfully!")
    print("\nGenerated files:")
    print("  - Business_Bay_2BR_CMA.pdf")
    print("  - Business_Bay_2BR_Comparables.csv")
    print("  - Top_Investors_Dubai.csv")
