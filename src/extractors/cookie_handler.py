from http.cookiejar import CookieJar
from typing import Optional
from requests.cookies import RequestsCookieJar
from requests.utils import cookiejar_from_dict

class CookieHandler:
    """
    Accepts a raw cookie string (e.g., 'name=value; name2=value2') and provides a RequestsCookieJar.
    """

    def __init__(self, cookie_string: str = ""):
        self.cookie_string = cookie_string or ""

    @staticmethod
    def _parse_cookie_string(cookie_string: str) -> dict:
        result = {}
        for part in cookie_string.split(";"):
            if "=" in part:
                name, value = part.strip().split("=", 1)
                result[name.strip()] = value.strip()
        return result

    def get_requests_cookiejar(self) -> Optional[RequestsCookieJar]:
        if not self.cookie_string.strip():
            return None
        d = self._parse_cookie_string(self.cookie_string)
        jar: CookieJar = cookiejar_from_dict(d)
        req_jar = RequestsCookieJar()
        for c in jar:
            req_jar.set(c.name, c.value, domain=c.domain or ".upwork.com", path=c.path or "/")
        return req_jar