from urllib.parse import urlencode

UPWORK_SEARCH_BASE = "https://www.upwork.com/nx/search/jobs/"

# Map internal filter config to Upwork query params (heuristic)
EXPERIENCE_MAP = {
    "entry": "entry_level",
    "intermediate": "intermediate",
    "expert": "expert",
}

PAYMENT_TYPE_MAP = {
    "hourly": "hourly",
    "fixed": "fixed-price",
}

def build_search_url(query: str, page: int, per_page: int, filter_cfg: dict) -> str:
    """
    Build a search URL for Upwork job search.
    Note: Upwork uses dynamic APIs; this URL targets SSR/HTML for scraping.
    """
    params = {
        "q": query,
        "sort": "recency",
        "page": page,
        "per_page": per_page,
    }

    # Experience filter
    exp = filter_cfg.get("experience")
    if isinstance(exp, list) and exp:
        params["experience_level"] = ",".join(EXPERIENCE_MAP.get(e.lower(), e.lower()) for e in exp)

    # Payment type
    pt = filter_cfg.get("payment_type")
    if isinstance(pt, list) and pt:
        params["payment_verification"] = "1" if filter_cfg.get("verified_only") else ""
        params["job_type"] = ",".join(PAYMENT_TYPE_MAP.get(p.lower(), p.lower()) for p in pt)

    # Weekly hours
    hours = filter_cfg.get("hours_per_week")
    if hours:
        params["hours_per_week"] = hours  # e.g., less_than_30, more_than_30

    # Budget min/max (heuristic)
    bmin = filter_cfg.get("budget_min")
    bmax = filter_cfg.get("budget_max")
    if bmin is not None:
        params["budget_min"] = bmin
    if bmax is not None:
        params["budget_max"] = bmax

    # Countries include or exclude (optional)
    include_countries = filter_cfg.get("include_countries")
    if include_countries:
        params["client_location"] = ",".join(include_countries)

    qs = urlencode({k: v for k, v in params.items() if v not in ("", None)})
    return f"{UPWORK_SEARCH_BASE}?{qs}"