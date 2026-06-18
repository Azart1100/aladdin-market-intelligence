import json
import os
import sys
import io
from datetime import datetime
from typing import Any, Optional

import google.generativeai as genai

# Import modules
sys.path.append(os.path.dirname(__file__))
from config import AladdinConfig
from yandex_wordstat import YandexWordstatOracle
from google_trends import GoogleTrendsOracle
from infrastructure_score import InfrastructureScore
from real_voice import RealVoice
from youtube_deep import YoutubeDeepScraper
from vk_scanner import VKScanner
from telegram_deep import TelegramDeepScanner
from maps_leads import GoogleMapsLeadExtractor


class PersonaGenerator:
    """Generates buyer persona profiles using Google Gemini LLM."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def generate(self, market_data: dict[str, Any]) -> dict[str, Any]:
        """Generate persona profiles from market data, or return a fallback prompt."""
        prompt = self._build_prompt(market_data)

        if not self.model:
            # Provide a fallback prompt for the agent to use manually
            return {
                "error": "Google API Key missing. Persona generation skipped.",
                "fallback_prompt": prompt,
                "hint": "Copy the fallback_prompt above into any LLM chat to generate personas manually."
            }

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except (json.JSONDecodeError, ValueError) as e:
            return {"error": f"LLM response parsing failed: {e}"}
        except Exception as e:
            return {"error": f"LLM Generation failed: {e}"}

    @staticmethod
    def _build_prompt(market_data: dict[str, Any]) -> str:
        """Build the persona generation prompt from market context."""
        return f"""\
Ты — ведущий эксперт по психографии и маркетингу в недвижимости. 
На основе предоставленных данных о рынке создай 3 детальных профиля покупателей (Персон).

ДАННЫЕ РЫНКА:
- Объект: {market_data.get('target')}
- Спрос: {market_data.get('demand_volume')} запросов/мес
- Инфраструктура (0-10): {market_data.get('infra_score')}
- Тональность отзывов (0-10): {market_data.get('sentiment')}
- Соцсети (сигналы): {market_data.get('social_signals')}
- Тренды Google: {market_data.get('trends_rising', 'Нет данных')}

ДЛЯ КАЖДОЙ ПЕРСОНЫ УКАЖИ:
1. Имя-архетип.
2. Психологический триггер.
3. Боли и страхи.
4. Стратегия оффера.

Верни ответ СТРОГО в формате JSON."""


class ProjectAladdin:
    """Orchestrator for 360° Market Intelligence reports."""

    def __init__(self, config: AladdinConfig):
        self.config = config
        self.yandex = YandexWordstatOracle(
            api_key=config.yandex_api_key or None,
            folder_id=config.yandex_folder_id or None,
        )
        self.google = GoogleTrendsOracle()
        self.infra = InfrastructureScore()
        self.voice = RealVoice()
        self.yt = YoutubeDeepScraper()
        self.vk = VKScanner()
        self.tg = TelegramDeepScanner(config=config)
        self.maps = GoogleMapsLeadExtractor()
        self.persona_gen = PersonaGenerator(api_key=config.google_api_key or None)

    def generate_report(self) -> dict[str, Any]:
        """Run full 360° market intelligence pipeline using self.config.phrase."""
        phrase = self.config.phrase
        print(f"🚀 [ALADDIN CORE] Starting 360° Market Intelligence for: '{phrase}'...")

        # 1. Base Analytics
        print("🔍 Analyzing Market Fundamentals...")
        y_data: dict[str, Any] = self.yandex.get_demand_data(phrase)
        infra_data: dict[str, Any] = self.infra.analyze(phrase)

        # 1b. Google Trends (imported but previously unused)
        print("📈 Fetching Google Trends data...")
        try:
            trends_data: dict[str, Any] = self.google.get_demand_data(phrase)
        except (ConnectionError, TimeoutError, Exception) as e:
            print(f"  ⚠️  Google Trends unavailable: {e}")
            trends_data = {"interest_over_time": [], "related_queries": {"top": [], "rising": []}}

        # 2. Deep Social Scrape
        print("📡 Performing Social Media Deep Scrape (YT, VK, TG, Maps)...")
        yt_data: dict[str, Any] = self.yt.analyze_market_sentiments(phrase)
        vk_data: dict[str, Any] = self.vk.scan_groups(phrase)
        tg_data: dict[str, Any] = self.tg.scan_channels(phrase)
        # Use config-driven location_query instead of hardcoded values
        maps_data: dict[str, Any] = self.maps.extract_nearby_businesses(self.config.location_query)

        # 3. Market Context for Persona
        social_signals: dict[str, int] = {
            "youtube_videos": yt_data.get('videos_found', 0),
            "vk_groups": len(vk_data.get('groups_found', [])),
            "tg_channels": len(tg_data.get('verified_communities', [])),
            "local_leads": len(maps_data.get('leads_found', []))
        }

        # Extract rising queries for persona context
        rising_queries = trends_data.get("related_queries", {}).get("rising", [])
        rising_labels = [q.get("query", "") for q in rising_queries[:5]] if isinstance(rising_queries, list) else []

        voice_data: dict[str, Any] = self.voice.analyze(phrase)
        sentiment_score: float = voice_data.get('sentiment_score', 5)

        market_context: dict[str, Any] = {
            "target": phrase,
            "demand_volume": sum(int(i['count']) for i in y_data.get('top', []) if 'count' in i),
            "infra_score": infra_data.get('infrastructure_score', 0),
            "sentiment": sentiment_score,
            "social_signals": social_signals,
            "geo_focus": [reg['region_name'] for reg in y_data.get('regions', [])[:5]],
            "trends_rising": rising_labels,
        }

        persona_profiles: dict[str, Any] = self.persona_gen.generate(market_context)

        if isinstance(persona_profiles, dict) and "fallback_prompt" in persona_profiles:
            print("\n🤖 [HYBRID MODE] Google API Key not found. Copy this context to the Agent for Persona generation:")
            print("-" * 30)
            print(persona_profiles["fallback_prompt"])
            print("-" * 30)

        # 4. Final Synthesis
        report: dict[str, Any] = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target": phrase,
            "config": {
                "city": self.config.city,
                "brand": self.config.brand,
                "district": self.config.district,
            },
            "core_metrics": {
                "demand": y_data,
                "infrastructure": infra_data,
                "trends": trends_data,
            },
            "social_intelligence": {
                "youtube": yt_data,
                "vk": vk_data,
                "telegram": tg_data,
                "maps": maps_data
            },
            "voice_of_customer": voice_data,
            "personas": persona_profiles,
            "insights": self.synthesize_insights(
                y_data, infra_data, social_signals, sentiment_score, trends_data
            )
        }

        return report

    def synthesize_insights(
        self,
        yandex: dict[str, Any],
        infra: dict[str, Any],
        social: dict[str, int],
        sentiment: float,
        trends: dict[str, Any],
    ) -> list[str]:
        """Generate actionable insights from all collected data sources."""
        insights: list[str] = []

        # --- Demand Analysis ---
        y_total = sum(int(item['count']) for item in yandex.get('top', []) if 'count' in item)
        if y_total > 1000:
            insights.append(
                f"DEMAND: Massive Search Heat ({y_total:,} requests/mo). Highly competitive niche."
            )
        elif y_total < 100:
            insights.append(
                f"DEMAND: Low search volume ({y_total} requests/mo). "
                f"Niche market — consider awareness campaigns before direct sales."
            )
        else:
            insights.append(f"DEMAND: Moderate search volume ({y_total:,} requests/mo).")

        # --- Infrastructure Score Interpretation ---
        infra_score = infra.get('infrastructure_score', 0)
        if infra_score < 4:
            insights.append(
                f"INFRA: Poor infrastructure rating ({infra_score}/10). "
                f"Highlight future development plans in marketing materials."
            )
        elif infra_score <= 7:
            insights.append(
                f"INFRA: Moderate infrastructure ({infra_score}/10). "
                f"Sufficient for most buyers, emphasize key amenities."
            )
        else:
            insights.append(
                f"INFRA: Strong infrastructure ({infra_score}/10). "
                f"Major selling point — feature prominently in all ads."
            )

        # --- Sentiment Interpretation ---
        if sentiment >= 7:
            insights.append(
                f"SENTIMENT: Positive market perception (score {sentiment}/10). "
                f"Leverage testimonials and social proof."
            )
        elif sentiment >= 4:
            insights.append(
                f"SENTIMENT: Mixed reviews (score {sentiment}/10). "
                f"Address common concerns proactively in sales collateral."
            )
        else:
            insights.append(
                f"SENTIMENT: Negative perception detected (score {sentiment}/10). "
                f"Reputation management is critical before scaling ad spend."
            )

        # --- Social Media Presence ---
        yt_count = social.get('youtube_videos', 0)
        tg_count = social.get('tg_channels', 0)
        vk_count = social.get('vk_groups', 0)
        if yt_count > 0 or tg_count > 0 or vk_count > 0:
            parts = []
            if yt_count:
                parts.append(f"{yt_count} YouTube videos")
            if vk_count:
                parts.append(f"{vk_count} VK groups")
            if tg_count:
                parts.append(f"{tg_count} Telegram channels")
            insights.append(f"SOCIAL: Active digital footprint — {', '.join(parts)}.")
        else:
            insights.append("SOCIAL: No significant social media presence detected.")

        # --- Google Trends Rising Queries ---
        rising = trends.get("related_queries", {}).get("rising", [])
        if isinstance(rising, list) and rising:
            top_rising = [q.get("query", "") for q in rising[:3]]
            insights.append(
                f"TRENDS: Rising search queries — {', '.join(top_rising)}. "
                f"Consider targeting these in SEO/content strategy."
            )

        return insights

    def save_report(
        self,
        report: dict[str, Any],
        filename: str = "aladdin_360_deep_report.json",
        output_dir: Optional[str] = None,
    ) -> str:
        """Save report JSON to a configurable output directory.

        Args:
            report: The report dictionary to save.
            filename: Output filename.
            output_dir: Directory to save into. Defaults to project root /output.

        Returns:
            Absolute path to the saved report file.
        """
        if output_dir is None:
            # Default: project root's output directory (not alongside code)
            output_dir = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', '..', 'output'
            )
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"✅ [ALADDIN CORE] Deep 360° Report generated: {filepath}")
        except OSError as e:
            print(f"❌ [ALADDIN CORE] Failed to save report: {e}", file=sys.stderr)
            raise
        return filepath


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    target_phrase = sys.argv[1] if len(sys.argv) > 1 else "жк светский лес"
    config = AladdinConfig.from_phrase(target_phrase)
    aladdin = ProjectAladdin(config)
    report = aladdin.generate_report()

    print("\n" + "═" * 60)
    print(f"📊 PROJECT ALADDIN DEEP SCAN: {report['target'].upper()}")
    print("═" * 60)

    print("\n💡 KEY INSIGHTS:")
    for insight in report['insights']:
        print(f"✨ {insight}")

    print("\n📡 SOCIAL FOOTPRINT:")
    yt_vids = report['social_intelligence']['youtube'].get('videos_found', 0)
    vk_groups = len(report['social_intelligence']['vk'].get('groups_found', []))
    tg_channels = len(report['social_intelligence']['telegram'].get('verified_communities', []))
    maps_leads = len(report['social_intelligence']['maps'].get('leads_found', []))
    print(f"   📺 YouTube: {yt_vids} sources")
    print(f"   👥 VK: {vk_groups} communities")
    print(f"   📱 Telegram: {tg_channels} verified channels")
    print(f"   📍 Local Business Leads: {maps_leads}")

    print("\n📈 GOOGLE TRENDS:")
    rising_qs = report['core_metrics']['trends'].get('related_queries', {}).get('rising', [])
    if isinstance(rising_qs, list) and rising_qs:
        for q in rising_qs[:5]:
            print(f"   🔥 {q.get('query', '?')} (value: {q.get('value', '?')})")
    else:
        print("   (no rising queries)")

    print("\n" + "═" * 60)
    aladdin.save_report(report)
