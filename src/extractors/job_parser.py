import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.cookies import RequestsCookieJar

from utils.time_utils import parse_relative_time_to_iso, now_iso

logger = logging.getLogger("job_parser")

UPWORK_BASE = "https://www.upwork.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

class UpworkJobParser:
    """
    Lightweight HTML parser for Upwork job search results pages.
    Works best with valid cookies. Without cookies, fewer fields may be present.
    """

    def __init__(self, cookies: Optional[RequestsCookieJar] = None, timeout: int = 30):
        self.cookies = cookies
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        if cookies:
            self.session.cookies.update(cookies)

    def fetch_and_parse(self, url: str, proxies: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        logger.debug("Fetching URL: %s", url)
        resp = self.session.get(url, timeout=self.timeout, proxies=proxies, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        return self._parse_html(html)

    def _parse_html(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")

        # Upwork’s job search markup evolves; we use robust heuristics.
        # Strategy:
        #  1) Look for containers carrying data-test selectors commonly used by Upwork.
        #  2) Fall back to card-like sections with job titles linking to /jobs/...
        jobs: List[Dict[str, Any]] = []

        # Pattern A: React SSR list items with data-test attributes
        list_candidates = soup.select("[data-test='job-tile-list'] li, li[data-test='job-tile-list-item']")
        if not list_candidates:
            # Pattern B: generic cards
            list_candidates = soup.select("section, article, li")

        for node in list_candidates:
            job = self._extract_job_from_node(node)
            if job:
                jobs.append(job)

        logger.debug("Parsed %d jobs from HTML", len(jobs))
        return jobs

    def _extract_job_from_node(self, node) -> Optional[Dict[str, Any]]:
        # Title + URL
        title_el = node.select_one("a[data-test='job-tile-title'], a[href*='/jobs/']")
        if not title_el:
            # Another fallback for heading anchors
            title_el = node.select_one("h2 a, h3 a")

        if not title_el or not title_el.get_text(strip=True):
            return None

        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        url = href if href.startswith("http") else urljoin(UPWORK_BASE, href)

        # Payment type, budget, experience
        payment_type = self._find_text(node, ["Hourly", "Fixed Price", "Fixed"])
        experience = self._find_text(node, ["Entry", "Intermediate", "Expert"])

        # Budget & hourly rate range heuristics
        budget_text = self._find_money_text(node)
        if not budget_text and payment_type and "Hourly" in payment_type:
            budget_text = self._find_text(node, ["per hour", "/hr", "$/hr"])

        # Proposals
        proposals = self._find_numeric_after(node, ["Proposals"])

        # Client country & rating (visible with cookies)
        location = self._find_country(node)
        rating = self._find_rating(node)

        # Posted time (may be relative like "3 hours ago")
        posted_text = self._find_text(node, ["ago", "hour", "minute", "day", "week", "month"])
        time_posted_iso = parse_relative_time_to_iso(posted_text) if posted_text else None

        # Description snippet
        desc_el = node.select_one("[data-test='job-description-text'], p, .text-body-sm")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""

        # Skills tags
        skills = [t.get_text(strip=True) for t in node.select("[data-test='token']")] or [
            s.get_text(strip=True) for s in node.select("a[href*='/o/profiles/skills/'], .o-tag-skill, .up-skill-badge")
        ]
        skills = [s for s in skills if s]

        job = {
            "Date Scraped": now_iso(),
            "Job ID": self._infer_job_id_from_url(url),
            "Time Posted": time_posted_iso or "",
            "Project Payment Type": payment_type or "",
            "Budget": budget_text or "",
            "Skill Level": experience or "",
            "Skills": skills,
            "Title": title,
            "URL": url,
            "Description": description,
            "Location": location or "",
            "Total Spent": "",  # requires job detail or client card; may be filled on detail fetch (not implemented)
            "Feedback": rating if rating is not None else "",
            "Proposals": proposals if proposals is not None else "",
            "Project Length": "",  # could be extracted from detail view
            "Weekly Hours": "",     # could be extracted from detail view
        }
        return job

    @staticmethod
    def _infer_job_id_from_url(url: str) -> str:
        # Upwork job urls typically contain a long numeric id or token
        # Heuristic: last sequence of digits 7+
        import re
        m = re.search(r"(\d{7,})", url)
        return m.group(1) if m else ""

    @staticmethod
    def _find_text(node, needles: List[str]) -> Optional[str]:
        text = node.get_text(" ", strip=True)
        for n in needles:
            if n.lower() in text.lower():
                # return a short window around the needle
                idx = text.lower().find(n.lower())
                start = max(0, idx - 24)
                end = min(len(text), idx + len(n) + 24)
                snippet = text[start:end]
                # clean snippet roughly
                snippet = " ".join(snippet.split())
                return snippet
        return None

    @staticmethod
    def _find_money_text(node) -> Optional[str]:
        import re
        text = node.get_text(" ", strip=True)
        # Match ranges like "$10.00-$20.00", "$50+", or "$1,000"
        m = re.search(r"\$\s?\d[\d,]*(\.\d{2})?(\s?-\s?\$\s?\d[\d,]*(\.\d{2})?)?|\$\s?\d[\d,]*\+?", text)
        return m.group(0) if m else None

    @staticmethod
    def _find_numeric_after(node, labels: List[str]) -> Optional[int]:
        import re
        text = node.get_text(" ", strip=True)
        for lbl in labels:
            m = re.search(rf"{lbl}\s*:\s*(\d+)", text, flags=re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    return None
        return None

    @staticmethod
    def _find_country(node) -> Optional[str]:
        # Countries often appear as a token or small text with a flag icon; fall back to capitalized word
        import re
        text = node.get_text(" ", strip=True)
        m = re.search(r"\b(United States|United Kingdom|Canada|Australia|Germany|France|India|Pakistan|"
                      r"Bangladesh|Philippines|Brazil|Spain|Italy|Netherlands|UAE|Saudi Arabia|Singapore|"
                      r"New Zealand|Poland|Mexico|Turkey|Japan|China|South Korea|South Africa)\b", text, re.I)
        return m.group(1) if m else None

    @staticmethod
    def _find_rating(node) -> Optional[float]:
        import re
        text = node.get_text(" ", strip=True)
        m = re.search(r"(\d\.\d{1,2})\s*/?\s*5", text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
        # Sometimes just "4.9" appears
        m2 = re.search(r"\b(\d\.\d{1,2})\b", text)
        if m2:
            try:
                val = float(m2.group(1))
                if 0.0 <= val <= 5.0:
                    return val
            except ValueError:
                return None
        return None