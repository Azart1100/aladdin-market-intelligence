import requests
from bs4 import BeautifulSoup
import json
import re

class CompetitorRadar:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def get_competitors(self, phrase="купить таунхаус в сочи"):
        # We'll search on Yandex as it's more localized for RU market
        url = f"https://yandex.ru/search/?text={phrase}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return {"error": f"Status code {response.status_code}"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            competitors = []
            # Look for organic and paid results
            # Note: Yandex classes change often. We'll look for generic links.
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'yandex.ru' in href or 'google.com' in href:
                    continue
                if href.startswith('http'):
                    domain = re.sub(r'https?://(www\.)?', '', href).split('/')[0]
                    if domain not in [c['domain'] for c in competitors] and len(competitors) < 10:
                        competitors.append({
                            "domain": domain,
                            "is_ad": "direct" in href or "adv" in str(a.parent)
                        })
            
            return {
                "phrase": phrase,
                "competitors": competitors
            }
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    radar = CompetitorRadar()
    print(json.dumps(radar.get_competitors(), indent=2, ensure_ascii=False))
