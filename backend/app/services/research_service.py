from urllib.parse import quote_plus

import httpx

from app.core.config import get_settings
from app.schemas.llm import ResearchReference


class ResearchService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def search_related_papers(self, query: str, limit: int = 5) -> list[ResearchReference]:
        if not self.settings.enable_research_search:
            return []

        query = " ".join(query.split())[:240]
        if not query:
            return []

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": str(limit),
            "fields": "title,year,url,venue",
        }
        headers = {}
        if self.settings.semantic_scholar_api_key:
            headers["x-api-key"] = self.settings.semantic_scholar_api_key

        try:
            response = httpx.get(url, params=params, headers=headers, timeout=8.0)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        references: list[ResearchReference] = []
        for item in payload.get("data", []):
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            references.append(
                ResearchReference(
                    title=title,
                    year=item.get("year"),
                    url=item.get("url"),
                    venue=item.get("venue"),
                )
            )
        return references

    def build_context(self, title: str, raw_text: str, limit: int = 5) -> str:
        query = title or raw_text[:160]
        references = self.search_related_papers(query=query, limit=limit)
        if not references:
            return (
                "External literature search unavailable or returned no reliable matches. "
                "Do not claim that future directions are novel; mark them as unverified."
            )
        lines = ["External literature search candidates:"]
        for reference in references:
            year = f" ({reference.year})" if reference.year else ""
            venue = f", {reference.venue}" if reference.venue else ""
            url = f", {reference.url}" if reference.url else ""
            lines.append(f"- {reference.title}{year}{venue}{url}")
        return "\n".join(lines)


def semantic_scholar_search_url(query: str) -> str:
    return f"https://www.semanticscholar.org/search?q={quote_plus(query)}&sort=relevance"


research_service = ResearchService()
