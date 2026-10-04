from abc import ABC, abstractmethod


class ImageProviderError(Exception):
    """Only safe public messages belong in this exception."""


class ImageProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def generate(self, prompt: str) -> bytes:
        """Return untrusted raster bytes; the image service validates and stores them."""
        raise NotImplementedError
