from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = (
    os.getenv("WORLD_FORK_API_BASE")
    or os.getenv("BACKEND_API_BASE")
    or "http://127.0.0.1:8003"
)
DEFAULT_API_PREFIX = "/api"
DEFAULT_TIMEOUT: float | None = None  # wait indefinitely; pass --timeout N to cap
DEFAULT_ENV_FILE = os.getenv("WORLD_FORK_ENV_FILE", ".env")


class WorldForkClient:
    """Thin synchronous HTTP client for the WorldFork backend.

    All paths are resolved against ``base_url + api_prefix`` unless they
    already start with ``http://`` or ``https://``. The CLI assumes every
    request lives under the ``/api`` namespace; the server is expected to
    expose ``/api/health`` (an alias of ``/health``).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_prefix: str = DEFAULT_API_PREFIX,
        timeout: float | None = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.strip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)

    def normalize_path(self, path: str) -> str:
        raw = path.strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        trimmed = raw.lstrip("/")
        if (
            self.api_prefix
            and not trimmed.startswith(f"{self.api_prefix}/")
            and trimmed != self.api_prefix
        ):
            return f"{self.api_prefix}/{trimmed}"
        return trimmed

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = self.normalize_path(path)
        try:
            response = self._http.request(method, url, json=json_body, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            message = exc.response.text
            raise RuntimeError(
                f"HTTP {exc.response.status_code} {exc.request.method} {url}: {message}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"request failed for {url}: {exc}") from exc

        if not response.text:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text
