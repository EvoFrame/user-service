import httpx

from src.libs.service_token_cache import ServiceTokenCache


class S2SClient:
    """HTTP client for authenticated service-to-service (S2S) communication.

    Automatically fetches and attaches a bearer service token to each request
    using the provided token cache.
    """

    def __init__(self, base_url: str, token_cache: ServiceTokenCache):
        self._base_url = base_url
        self._token_cache = token_cache

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """Send an authenticated POST request to the target service.

        Retrieves a current service token from the cache and attaches it as an
        ``X-Service-Token`` bearer header before performing the POST.

        Args:
            path: URL path relative to the configured base URL.
            **kwargs: Additional keyword arguments forwarded to
                ``httpx.AsyncClient.post``.

        Returns:
            The raw httpx response from the downstream service.
        """
        token = await self._token_cache.get()
        headers = kwargs.pop("headers", {})
        headers["X-Service-Token"] = f"Bearer {token}"
        async with httpx.AsyncClient(base_url=self._base_url, timeout=30.0) as client:
            return await client.post(path, headers=headers, **kwargs)
