from datetime import datetime

import arxiv
import os
import requests
from dotenv import load_dotenv

load_dotenv()


def search_arxiv(query, max_results=5):
    search = arxiv.Search(
        query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
    )
    results = []
    for result in search.results():
        results.append(
            {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary[:300] + "..."
                if len(result.summary) > 300
                else result.summary,
                "url": result.entry_id,
                "date": result.published.strftime("%Y-%m-%d"),
            }
        )
    return results


def search_hacker_news(query: str, max_results=5):
    # This searches for stories containing the query, sorted by relevance
    url = "https://hn.algolia.com/api/v1/search_by_date"
    params = {"query": query, "tags": "story", "hitsPerPage": max_results}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Automatically checks for 200 OK

        data = response.json()

        results = []
        for hit in data.get("hits", []):
            external_url = hit.get("url")
            object_id = hit.get("objectID")  # Algolia uses objectID for the HN ID

            # If url is None, create a link to the HN comment page
            final_url = (
                external_url
                if external_url
                else f"https://news.ycombinator.com/item?id={object_id}"
            )

            results.append(
                {
                    "source": "Hacker News",
                    "title": hit.get("title"),
                    "url": final_url,
                    "points": hit.get("points"),
                    "date": datetime.fromtimestamp(hit.get("created_at_i")).strftime(
                        "%Y-%m-%d"
                    ),
                }
            )
        return results
    except Exception as e:
        print(f"Error fetching Hacker News data: {e}")
        return []


def search_the_guardian(query: str, api_key: str, max_results=5):
    url = "https://content.guardianapis.com/search"
    params = {
        "q": query,
        "api-key": api_key,
        "page-size": max_results,
        "order-by": "newest",
        "show-fields": "trailText",  # This gives a nice short summary
    }
    response = requests.get(url, params=params).json()
    results = []
    for r in response.get("response", {}).get("results", []):
        results.append(
            {
                "source": "The Guardian",
                "title": r.get("webTitle"),
                "url": r.get("webUrl"),
                "summary": r.get("fields", {}).get("trailText", ""),
                "date": r.get("webPublicationDate")[:10],
            }
        )
    print(f"DEBUG: Found {len(results)} articles for {query}")
    return results


if __name__ == "__main__":
    # Example usage
    print("Searching arXiv for 'machine learning'...")
    arxiv_results = search_arxiv("machine learning")
    for res in arxiv_results:
        print(res)

    print("\nSearching Hacker News for 'AI'...")
    hn_results = search_hacker_news("code")
    for res in hn_results:
        print(res)

    print("\nSearching The Guardian...")
    guardian_results = search_the_guardian(
        "Gaza", api_key=os.getenv("GUARDIAN_API_KEY")
    )
    for res in guardian_results:
        print(res)
