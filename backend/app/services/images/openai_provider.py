import base64
import binascii
import json
import httpx
from app.core.config import Settings
from app.services.images.base import ImageProvider, ImageProviderError


class OpenAIImageProvider(ImageProvider):
    name = "openai"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.model = settings.image_model
        self.transport = transport

    async def generate(self, prompt: str) -> bytes:
        payload = {"model": self.model, "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "low", "output_format": "png"}
        try:
            async with httpx.AsyncClient(timeout=self.settings.image_timeout_seconds, transport=self.transport) as client:
                async with client.stream("POST", "https://api.openai.com/v1/images/generations", headers={"Authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}"}, json=payload) as response:
                    if response.status_code == 429: raise ImageProviderError("Illustration generation is busy. Please try again later.")
                    if response.status_code >= 400: raise ImageProviderError("The illustration service couldn't complete this request. Please try again later.")
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > self.settings.image_max_bytes * 2 + 65536:
                            raise ImageProviderError("The illustration response was too large.")
            body = json.loads(chunks)
            data = body["data"]
            if len(data) != 1: raise ValueError("Expected one image")
            # No remote URL downloads: avoids expiring assets and arbitrary provider-controlled hosts.
            encoded = data[0]["b64_json"]
            image = base64.b64decode(encoded, validate=True)
            if not image or len(image) > self.settings.image_max_bytes: raise ValueError("Invalid image size")
            return image
        except httpx.TimeoutException:
            raise ImageProviderError("Illustration generation took too long. Please try again.") from None
        except httpx.RequestError:
            raise ImageProviderError("The illustration service is unavailable. Please try again.") from None
        except (KeyError, TypeError, ValueError, binascii.Error):
            raise ImageProviderError("The illustration service returned an unreadable image.") from None
