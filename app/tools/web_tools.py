from ddgs import DDGS
import time
from langchain.tools import tool
import re
import requests
from bs4 import BeautifulSoup
from typing import Optional,Any,Dict
@tool
def web_search_tool(query:str) -> dict:
    """Search the internet using DuckDuckGo for real-time information, specific dates, historical records, weather, AQI, news, and facts not in your training data."""

    max_results = 2
    max_retries = 3

    for attempt in range(max_retries):

        try:
            with DDGS(timeout=20) as ddgs:

                results = list(
                    ddgs.text(
                        query,
                        max_results=max_results
                    )
                )

            if results:

                formatted_results = [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    }
                    for r in results
                ]

                return {
                    "status": "success",
                    "results": formatted_results,
                    "total_results": len(formatted_results)
                }

        except Exception as e:
            pass

        if attempt < max_retries - 1:
            time.sleep(2)

    return {
        "status": "error",
        "error": "Web search failed after multiple attempts."
    }

@tool
def browse_webpage_tool(URL: str, params: Optional[Dict[str, Any]] = None, max_chars: int = 5000) -> dict:
    """Fetch a webpage and extract readable content within a character limit."""

    try:
        # Validate URL
        if not re.match(r"^https?://", URL):
            return {
                "status": "error",
                "error": "Invalid URL. URL must start with http:// or https://"
            }

        # Fetch webpage
        response = requests.get(
            url=URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove irrelevant elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        # Page title
        page_title = soup.title.get_text(strip=True) if soup.title else ""

        # Main headings
        headings = [
            heading.get_text(" ", strip=True)
            for heading in soup.find_all(["h1", "h2", "h3"])
            if heading.get_text(strip=True)
        ]

        # Paragraphs
        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in soup.find_all("p")
            if paragraph.get_text(strip=True)
        ]

        # Lists
        lists = [
            item.get_text(" ", strip=True)
            for item in soup.find_all("li")
            if item.get_text(strip=True)
        ]

        # Links
        links = []

        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)
            url = anchor.get("href")

            if text:
                links.append({
                    "text": text,
                    "url": url
                })

        # Apply character limit
        char_count = 0

        def add_text(items):
            nonlocal char_count

            limited_items = []

            for item in items:
                if isinstance(item, dict):
                    item_size = len(item.get("text", "")) + len(item.get("url", ""))
                else:
                    item_size = len(item)

                if char_count + item_size > max_chars:
                    break

                limited_items.append(item)
                char_count += item_size

            return limited_items

        # Preserve priority: title → headings → paragraphs → lists → links
        limited_headings = add_text(headings)
        limited_paragraphs = add_text(paragraphs)
        limited_lists = add_text(lists)
        limited_links = add_text(links)

        return {
            "status": "success",
            "content": {
                "title": page_title,
                "headings": limited_headings,
                "paragraphs": limited_paragraphs,
                "lists": limited_lists,
                "links": limited_links
            }
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": f"Request failed: {str(e)}"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

