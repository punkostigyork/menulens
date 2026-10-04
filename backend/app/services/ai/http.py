import httpx
from app.services.ai.base import ProviderError


async def post_json(client: httpx.AsyncClient, url: str, headers: dict, payload: dict) -> dict:
    try:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict): raise ValueError("Invalid envelope")
        return body
    except httpx.TimeoutException:
        raise ProviderError("Understanding this menu took too long. Please try again.", 504) from None
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise ProviderError("Menu processing is busy right now. Please try again later.", 503) from None
        raise ProviderError("The menu processing service is unavailable. Please check its configuration or try again later.") from None
    except (httpx.RequestError, ValueError):
        raise ProviderError("The menu processing service returned an unreadable response. Please try again.") from None
