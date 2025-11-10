import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from extractors.job_parser import UpworkJobParser
from extractors.proxy_manager import ProxyManager
from extractors.cookie_handler import CookieHandler
from filters.query_builder import build_search_url
from filters.pagination import PagePlan
from utils.logger import configure_logging
from utils.time_utils import now_iso
from output.data_exporter import DataExporter

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upwork Job Scraper – fetches structured job listings."
    )
    parser.add_argument(
        "--input",
        default=os.path.join(os.path.dirname(__file__), "..", "data", "input.example.json"),
        help="Path to input JSON configuration.",
    )
    parser.add_argument(
        "--outdir",
        default=os.path.join(os.path.dirname(__file__), "..", "data"),
        help="Directory to write output files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    configure_logging(level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger("main")

    try:
        config = load_json(os.path.abspath(args.input))
    except Exception as e:
        logger.exception("Failed to load input JSON: %s", e)
        sys.exit(1)

    # Prepare runtime configuration
    queries: List[str] = config.get("queries", [])
    if not queries:
        logger.warning("No queries provided. Using default ['web scraping'] for demo.")
        queries = ["web scraping"]

    pages = max(1, int(config.get("pages", 1)))
    per_page = max(1, int(config.get("per_page", 10)))
    filters = config.get("filters", {}) or {}

    # Cookies & proxies
    cookie_string = config.get("cookies", "")
    use_proxies = bool(config.get("use_proxies", False))
    proxy_file = config.get("proxy_source") or os.path.join(
        os.path.dirname(__file__), "..", "data", "proxies.txt"
    )

    cookie_handler = CookieHandler(cookie_string=cookie_string)
    session_cookies = cookie_handler.get_requests_cookiejar()

    proxy_manager = ProxyManager(proxy_file) if use_proxies else None

    exporter = DataExporter()
    parser_engine = UpworkJobParser(cookies=session_cookies)

    ensure_dir(args.outdir)

    all_results: List[Dict[str, Any]] = []
    run_started = now_iso()
    logger.info("Scrape started at %s", run_started)

    for q in queries:
        page_plan = PagePlan(total_pages=pages, per_page=per_page)
        logger.info("Query '%s' with %d pages × %d per page", q, pages, per_page)

        for p in page_plan.iter_pages():
            url = build_search_url(
                query=q,
                page=p,
                per_page=per_page,
                filter_cfg=filters,
            )

            # Rotate proxy (if any)
            proxies = proxy_manager.next_requests_proxy() if proxy_manager else None
            try:
                batch = parser_engine.fetch_and_parse(url=url, proxies=proxies)
            except Exception as e:
                logger.exception("Error parsing page %s: %s", url, e)
                batch = []

            # Inject metadata & limit to per_page if upstream returns more
            for item in batch[:per_page]:
                item.setdefault("Date Scraped", now_iso())
                item.setdefault("Query", q)
                item.setdefault("Source", "Upwork Jobs Search")
                all_results.append(item)

            logger.info(
                "Query '%s' page %d: collected %d items (total=%d)",
                q,
                p,
                len(batch[:per_page]),
                len(all_results),
            )

    # Export
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    json_path = os.path.join(args.outdir, f"upwork_jobs_{timestamp}.json")
    csv_path = os.path.join(args.outdir, f"upwork_jobs_{timestamp}.csv")

    exporter.to_json(all_results, json_path)
    exporter.to_csv(all_results, csv_path)

    logger.info("Wrote JSON -> %s", json_path)
    logger.info("Wrote CSV  -> %s", csv_path)
    logger.info("Scrape finished at %s (items=%d)", now_iso(), len(all_results))

if __name__ == "__main__":
    main()