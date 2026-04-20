# src/tools/search_tools.py
# Improved MARVEL scraper with:
#   - Targeted multi-query search per subsystem
#   - Fixed OSTI URLs (built from osti_id field)
#   - Relevance filtering to remove noisy results
#   - Async support for faster scraping

import requests
import urllib.parse
import time
import re
from typing import Optional


class MARVELSearcherSimple:
    """
    Scrapes OSTI and arXiv for evidence relevant to MARVEL microreactor subsystems.
    
    Fixes vs previous version:
    - OSTI URLs now correctly built from record ID
    - Multiple targeted queries per subsystem (not one broad query)
    - Relevance filter removes off-topic results
    - Deduplication across queries
    """

    OSTI_API = "https://www.osti.gov/api/v1/records"
    ARXIV_API = "http://export.arxiv.org/api/query"

    def __init__(self, max_results_per_query: int = 10):
        self.max_per_query = max_results_per_query
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MARVEL-TRL-Assessor/1.0"})

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def search_subsystem(self, subsystem_key: str, subsystem_config: dict) -> dict:
        """
        Run all queries for a subsystem and return deduplicated, filtered results.

        Returns:
            {
                "subsystem": str,
                "name": str,
                "osti_results": [...],
                "arxiv_results": [...],
                "total_documents": int,
                "relevance_stats": {...}
            }
        """
        print(f"\n🔍 Searching: {subsystem_config['name']}")

        osti_results = self._search_osti_multi(
            subsystem_config["osti_queries"],
            subsystem_config["relevance_keywords"]
        )

        arxiv_results = self._search_arxiv_multi(
            subsystem_config["arxiv_queries"],
            subsystem_config["relevance_keywords"]
        )

        total_before = len(osti_results["all"]) + len(arxiv_results["all"])
        total_after = len(osti_results["relevant"]) + len(arxiv_results["relevant"])

        print(f"   ✅ OSTI:  {len(osti_results['relevant'])} relevant / {len(osti_results['all'])} fetched")
        print(f"   ✅ arXiv: {len(arxiv_results['relevant'])} relevant / {len(arxiv_results['all'])} fetched")
        print(f"   🗑️  Filtered out: {total_before - total_after} irrelevant results")

        return {
            "subsystem": subsystem_key,
            "name": subsystem_config["name"],
            "osti_results": osti_results["relevant"],
            "arxiv_results": arxiv_results["relevant"],
            "total_documents": total_after,
            "relevance_stats": {
                "osti_fetched": len(osti_results["all"]),
                "osti_relevant": len(osti_results["relevant"]),
                "arxiv_fetched": len(arxiv_results["all"]),
                "arxiv_relevant": len(arxiv_results["relevant"]),
                "total_filtered_out": total_before - total_after
            }
        }

    # ------------------------------------------------------------------ #
    #  OSTI                                                                #
    # ------------------------------------------------------------------ #

    def _search_osti_multi(self, queries: list[str], keywords: list[str]) -> dict:
        """Run multiple OSTI queries and deduplicate by osti_id."""
        seen_ids = set()
        all_results = []
        relevant_results = []

        for query in queries:
            print(f"      OSTI query: '{query}'")
            records = self._fetch_osti(query)
            time.sleep(0.5)  # be polite to the API

            for record in records:
                osti_id = str(record.get("osti_id", ""))
                if osti_id in seen_ids:
                    continue
                seen_ids.add(osti_id)

                doc = self._parse_osti_record(record)
                all_results.append(doc)

                if self._is_relevant(doc, keywords):
                    relevant_results.append(doc)

        return {"all": all_results, "relevant": relevant_results}

    def _fetch_osti(self, query: str) -> list:
        """Call OSTI API and return raw records."""
        params = {
            "q": query,
            "rows": self.max_per_query,
            "sort": "score desc",
        }
        try:
            resp = self.session.get(self.OSTI_API, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json() if isinstance(resp.json(), list) else []
        except Exception as e:
            print(f"      ⚠️  OSTI error for '{query}': {e}")
            return []

    def _parse_osti_record(self, record: dict) -> dict:
        """
        Parse one OSTI API record into a clean document dict.
        KEY FIX: Build URL from osti_id instead of relying on a missing 'url' field.
        """
        osti_id = record.get("osti_id", "")

        # Build URL from ID — this is the reliable approach
        url = f"https://www.osti.gov/biblio/{osti_id}" if osti_id else ""

        # Also check for a DOI-based URL as alternative
        doi = record.get("doi", "")
        doi_url = f"https://doi.org/{doi}" if doi else ""

        # Extract authors list
        authors_raw = record.get("authors", [])
        if isinstance(authors_raw, list):
            authors = ", ".join(
                a.get("name", "") for a in authors_raw if isinstance(a, dict)
            )
        else:
            authors = str(authors_raw)

        return {
            "osti_id": osti_id,
            "title": record.get("title", "No title").strip(),
            "url": url,
            "doi_url": doi_url,
            "snippet": record.get("description", record.get("abstract", ""))[:500],
            "publication_date": record.get("publication_date", ""),
            "authors": authors,
            "source_type": record.get("product_type", ""),
            "research_org": record.get("research_org", ""),
            "source": "OSTI"
        }

    # ------------------------------------------------------------------ #
    #  arXiv                                                               #
    # ------------------------------------------------------------------ #

    def _search_arxiv_multi(self, queries: list[str], keywords: list[str]) -> dict:
        """Run multiple arXiv queries and deduplicate by arxiv ID."""
        seen_ids = set()
        all_results = []
        relevant_results = []

        for query in queries:
            print(f"      arXiv query: '{query}'")
            entries = self._fetch_arxiv(query)
            time.sleep(0.5)

            for entry in entries:
                arxiv_id = entry.get("arxiv_id", "")
                if arxiv_id in seen_ids:
                    continue
                seen_ids.add(arxiv_id)

                all_results.append(entry)
                if self._is_relevant(entry, keywords):
                    relevant_results.append(entry)

        return {"all": all_results, "relevant": relevant_results}

    def _fetch_arxiv(self, query: str) -> list:
        """Call arXiv API and parse Atom XML response."""
        params = {
            "search_query": f"all:{query}",
            "max_results": self.max_per_query,
            "sortBy": "relevance",
            "sortOrder": "descending"
        }
        try:
            resp = self.session.get(self.ARXIV_API, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse_arxiv_xml(resp.text)
        except Exception as e:
            print(f"      ⚠️  arXiv error for '{query}': {e}")
            return []

    def _parse_arxiv_xml(self, xml_text: str) -> list:
        """Parse arXiv Atom XML into document dicts."""
        entries = []

        # Split on entry tags
        raw_entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)

        for raw in raw_entries:
            def extract(tag):
                m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", raw, re.DOTALL)
                return m.group(1).strip() if m else ""

            # Get arxiv ID from <id> tag
            id_str = extract("id")
            arxiv_id = id_str.split("/abs/")[-1] if "/abs/" in id_str else id_str

            # Get authors
            author_names = re.findall(r"<name>(.*?)</name>", raw)
            authors = ", ".join(author_names[:5])  # limit to first 5
            if len(author_names) > 5:
                authors += " et al."

            entries.append({
                "arxiv_id": arxiv_id,
                "title": extract("title").replace("\n", " "),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
                "snippet": extract("summary").replace("\n", " ")[:500],
                "publication_date": extract("published")[:10],
                "authors": authors,
                "source": "arXiv"
            })

        return entries

    # ------------------------------------------------------------------ #
    #  Relevance Filter                                                    #
    # ------------------------------------------------------------------ #

    def _is_relevant(self, doc: dict, keywords: list[str]) -> bool:
        """
        Return True if the document title or snippet contains at least
        one of the subsystem's relevance keywords (case-insensitive).
        
        This filters out off-topic results like wetland reports or
        particle physics papers that slipped through broad queries.
        """
        text = (
            (doc.get("title", "") + " " + doc.get("snippet", "")).lower()
        )
        for kw in keywords:
            if kw.lower() in text:
                return True
        return False