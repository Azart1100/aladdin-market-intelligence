from pytrends.request import TrendReq
import json
import pandas as pd
import time
import os

class GoogleTrendsOracle:
    def __init__(self, hl='ru-RU', tz=180):
        self.pytrends = TrendReq(hl=hl, tz=tz)

    def get_interest_over_time(self, phrase, timeframe='today 12-m', geo='RU'):
        try:
            self.pytrends.build_payload([phrase], timeframe=timeframe, geo=geo)
            df = self.pytrends.interest_over_time()
            if df.empty:
                return []
            df = df.reset_index()
            # Convert timestamp to string
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            return df.to_dict(orient='records')
        except Exception as e:
            return {"error": str(e)}

    def get_related_queries(self, phrase, timeframe='today 12-m', geo='RU'):
        try:
            self.pytrends.build_payload([phrase], timeframe=timeframe, geo=geo)
            related = self.pytrends.related_queries()
            result = {}
            if phrase in related:
                for key in ['top', 'rising']:
                    if related[phrase][key] is not None:
                        result[key] = related[phrase][key].to_dict(orient='records')
                    else:
                        result[key] = []
            return result
        except Exception as e:
            return {"error": str(e)}

    def get_demand_data(self, phrase):
        """High-level method for Aladdin synthesis"""
        return {
            "interest_over_time": self.get_interest_over_time(phrase),
            "related_queries": self.get_related_queries(phrase)
        }

if __name__ == "__main__":
    import sys
    phrase = sys.argv[1] if len(sys.argv) > 1 else "таунхаус сочи"
    oracle = GoogleTrendsOracle()
    print(json.dumps(oracle.get_demand_data(phrase), indent=2, ensure_ascii=False))
