import json
import os
import sys
from datetime import datetime

# Import our modules
sys.path.append(os.path.dirname(__file__))
from yandex_wordstat import YandexWordstatOracle
from google_trends import GoogleTrendsOracle
from supply_scanner import SupplyScanner
from competitor_radar import CompetitorRadar

class ProjectAladdin:
    def __init__(self):
        self.yandex = YandexWordstatOracle()
        self.google = GoogleTrendsOracle()
        self.supply = SupplyScanner()
        self.radar = CompetitorRadar()

    def generate_report(self, phrase="таунхаус сочи"):
        print(f"🚀 [ALADDIN CORE] Starting 360° Market Intelligence for: '{phrase}'...")
        
        # 1. Demand Analysis
        print("🔍 [MODULE: DEMAND] Analyzing Yandex & Google Trends...")
        yandex_data = self.yandex.get_demand_data(phrase)
        google_data = self.google.get_demand_data(phrase)
        
        # 2. Supply Analysis
        print("🏠 [MODULE: SUPPLY] Scanning Real Estate Aggregators...")
        supply_data = self.supply.scan_sochi_townhouses()
        
        # 3. Competitor Analysis
        print("📡 [MODULE: RADAR] Detecting Active Competitors...")
        radar_data = self.radar.get_competitors(f"купить {phrase}")
        
        # 4. Synthesis
        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": phrase,
            "demand": {
                "yandex": yandex_data,
                "google": google_data
            },
            "supply": supply_data,
            "competition": radar_data,
            "insights": self.synthesize_insights(yandex_data, google_data, supply_data, radar_data)
        }
        
        return report

    def synthesize_insights(self, yandex, google, supply, radar):
        insights = []
        
        # 1. Demand Heatmap
        y_total = sum(int(item['count']) for item in yandex.get('top', []) if 'count' in item)
        if y_total > 500:
            insights.append(f"DEMAND: High Search Heat ({y_total} requests/mo). The market is very active.")
        
        commercial_count = sum(1 for item in yandex.get('top', []) if item.get('intent') == 'COMMERCIAL')
        if commercial_count > 5:
            insights.append(f"INTENT: Strong Purchase Signal. {commercial_count} clusters of users are actively looking to buy/rent.")

        # 2. Supply Saturation
        listing_count = supply.get('listing_count')
        if listing_count and listing_count != 'unknown':
            try:
                count_int = int(listing_count)
                if count_int < 100:
                    insights.append(f"SUPPLY: Low Inventory Alert ({count_int} listings). This is a Seller's Market.")
                else:
                    insights.append(f"SUPPLY: High Inventory ({count_int} listings). Market is saturated, buyer's have choices.")
            except: pass
            
        # 3. Price Benchmark
        if supply.get('avg_price'):
            insights.append(f"PRICING: Average Market Entry is ~{supply['avg_price']:,.0f} ₽.")

        # 4. Competitor Landscape
        comp_count = len(radar.get('competitors', []))
        if comp_count > 5:
            insights.append(f"COMPETITION: Aggressive Advertising. Found {comp_count} active domains fighting for this traffic.")
            
        # 5. Geolocation Insight
        sochi_affinity = next((r for r in yandex.get('regions', []) if r['region_name'] == 'Сочи'), None)
        if sochi_affinity and float(sochi_affinity.get('affinityIndex', 0)) > 5000:
            insights.append("GEO: Hyper-local demand. Most searches are originating directly from Sochi residents.")

        return insights

    def save_report(self, report, filename="aladdin_full_report.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"✅ [ALADDIN CORE] 360° Report generated and saved to {filename}")

if __name__ == "__main__":
    target_phrase = sys.argv[1] if len(sys.argv) > 1 else "таунхаус сочи"
    aladdin = ProjectAladdin()
    report = aladdin.generate_report(target_phrase)
    
    # Summary Table Output
    print("\n" + "═"*60)
    print(f"📊 PROJECT ALADDIN: {report['target'].upper()} INTELLIGENCE")
    print("═"*60)
    for insight in report['insights']:
        print(f"✨ {insight}")
    print("═"*60)
    
    aladdin.save_report(report)
