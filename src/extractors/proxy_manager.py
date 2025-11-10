import itertools
import logging
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger("proxy_manager")

class ProxyManager:
    """
    Simple rotating proxy manager. Supports lines such as:
      http://user:pass@host:port
      http://host:port
      socks5://user:pass@host:port
    """

    def __init__(self, proxy_file: str):
        self.proxy_file = proxy_file
        self._proxies = self._load(proxy_file)
        self._cycler: Iterator[str] = itertools.cycle(self._proxies) if self._proxies else itertools.cycle([""])

    def _load(self, path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines()]
            proxies = [ln for ln in lines if ln and not ln.startswith("#")]
            logger.info("Loaded %d proxies from %s", len(proxies), path)
            return proxies
        except FileNotFoundError:
            logger.warning("Proxy file not found: %s", path)
            return []

    def next(self) -> Optional[str]:
        if not self._proxies:
            return None
        return next(self._cycler)

    def next_requests_proxy(self) -> Optional[Dict[str, str]]:
        url = self.next()
        if not url:
            return None
        # requests expects a dict for both http and https
        return {"http": url, "https": url}