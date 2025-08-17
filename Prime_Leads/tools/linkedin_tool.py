import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

class LinkedInTool:
    """
    A tool to search LinkedIn profiles using SerpAPI and Google Search
    """
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")

    def _run(self, query: str):
        all_results = []
        print(f"Searching LinkedIn profiles for query: {query}")
        for start in range(0, 40, 20):  
            params = {
                "engine": "google",
                "q": f"site:linkedin.com/in {query}",
                "api_key": self.api_key,
                "num": 20,
                "start": start
            }

            search = GoogleSearch(params)
            result_dict = search.get_dict()
            data = result_dict.get("organic_results", [])

            results_page = [
                {
                    "name": r.get("title"),
                    "profile_link": r.get("link"),
                    "snippet": r.get("snippet", "")
                }
                for r in data
            ]

            all_results.extend(results_page)

        return all_results
