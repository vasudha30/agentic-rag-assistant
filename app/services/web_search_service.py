"""Web search service backed by DuckDuckGo's HTML endpoint."""

from __future__ import annotations

import html
import logging
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)


class _DuckDuckGoResultsParser(HTMLParser):
    """Extract result titles, URLs, and snippets from DuckDuckGo HTML."""

    def __init__(self, max_results: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_results = max_results
        self.results: list[dict[str, str]] = []
        self._active_field: str | None = None
        self._active_parts: list[str] = []
        self._active_url = ""
        self._active_result: dict[str, str] | None = None

    @staticmethod
    def _has_class(attrs: list[tuple[str, str | None]], class_name: str) -> bool:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        return class_name in classes

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)

        if tag == "a" and self._has_class(attrs, "result__a"):
            self._active_field = "title"
            self._active_parts = []
            self._active_url = self._normalize_url(attributes.get("href") or "")
        elif tag in {"a", "div"} and self._has_class(attrs, "result__snippet"):
            self._active_field = "snippet"
            self._active_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_field is not None:
            cleaned = data.strip()
            if cleaned:
                self._active_parts.append(cleaned)

    def handle_endtag(self, tag: str) -> None:
        if self._active_field == "title" and tag == "a":
            title = " ".join(self._active_parts).strip()
            if title and self._active_url.startswith(("http://", "https://")):
                self._active_result = {
                    "title": title,
                    "url": self._active_url,
                    "snippet": "",
                }
                self.results.append(self._active_result)
            self._active_field = None
            self._active_parts = []
            self._active_url = ""
        elif self._active_field == "snippet" and tag in {"a", "div"}:
            snippet = " ".join(self._active_parts).strip()
            if self._active_result is not None and snippet:
                self._active_result["snippet"] = snippet
            self._active_field = None
            self._active_parts = []

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Unwrap DuckDuckGo redirect links when they contain a destination."""
        url = html.unescape(url).strip()
        parsed = urlparse(url)
        if "duckduckgo.com" in parsed.netloc.lower():
            destination = parse_qs(parsed.query).get("uddg", [None])[0]
            if destination:
                return html.unescape(destination)
        return url


def _clean_text(value: str) -> str:
    return " ".join(html.unescape(value).split())


class WebSearchService:
    """Search the public web and return structured results."""

    SEARCH_URL = "https://html.duckduckgo.com/html/"

    def __init__(self, timeout: float = 15.0) -> None:
        """Initialize the web search service."""
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._timeout = timeout

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> list[dict[str, str]]:
        """Search the web and return title, URL, and snippet."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Search query cannot be empty.")
        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        try:
            response = httpx.post(
                self.SEARCH_URL,
                data={"q": normalized_query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=self._timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("DuckDuckGo request failed")
            raise

        content_type = response.headers.get("content-type", "")
        logger.info(
            "DuckDuckGo response received: status=%s content_type=%s bytes=%s",
            response.status_code,
            content_type,
            len(response.content),
        )

        results = self._parse_results(
            response.text,
            max_results=max_results,
        )

        if not results:
            logger.warning(
                "DuckDuckGo returned no parseable results (status=%s, bytes=%s). "
                "The response may be a challenge page or the page structure "
                "may have changed.",
                response.status_code,
                len(response.content),
            )

        return results

    @staticmethod
    def _parse_results(
        html_content: str,
        *,
        max_results: int,
    ) -> list[dict[str, str]]:
        """Extract organic search results from DuckDuckGo HTML."""
        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        parser = _DuckDuckGoResultsParser(max_results=max_results)
        parser.feed(html_content)
        parser.close()

        results: list[dict[str, str]] = []
        for result in parser.results:
            url = result["url"]
            if "y.js?" in url or "ad_domain=" in url:
                continue

            results.append(
                {
                    "title": _clean_text(result["title"]),
                    "url": url,
                    "snippet": _clean_text(result.get("snippet", "")),
                }
            )
            if len(results) >= max_results:
                break

        return results
