import logging
import sys
import time
from curl_cffi import requests as cffi_requests
from core.domain.interfaces.http import BaseHttpClient

class HttpClient(BaseHttpClient):
    def __init__(
        self,
        base_delay: float = 2.0,
        max_retries: int = 3,
        timeout: int = 15,
        user_agent: str = "Mozilla/5.0",
        impersonate: str = "chrome",
        logger: logging.Logger | None = None,
    ):
        self._base_delay = base_delay
        self._max_retries = max_retries
        self._timeout = timeout
        self._user_agent = user_agent
        self._impersonate = impersonate
        self.logger = logger or logging.getLogger("core.http")
        
        self._session = cffi_requests.Session()
        self._session.headers.update({"User-Agent": self._user_agent})

    def fetch(self, url: str) -> bytes | None:
        for attempt in range(self._max_retries):
            current_delay = self._base_delay * (3**attempt)
            time.sleep(current_delay)

            try:
                response = self._session.get(
                    url,
                    impersonate=self._impersonate,
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    return response.content
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = (
                        int(retry_after)
                        if retry_after and retry_after.isdigit()
                        else (20 * (attempt + 1))
                    )
                    self.logger.warning(
                        f"[Rate Limit 429] {url} — waiting {wait}s before retry..."
                    )
                    time.sleep(wait)
                    continue
                else:
                    self.logger.error(
                        f"HTTP {response.status_code} fetching {url}"
                    )
                    break

            except Exception as e:
                self.logger.error(
                    f"Error fetching {url} (attempt {attempt + 1}): {e}"
                )

        return None

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            pass
