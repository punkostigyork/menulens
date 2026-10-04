from app.core.config import Settings
from app.core.errors import ServiceError
from app.services.images.base import ImageProvider
from app.services.images.openai_provider import OpenAIImageProvider

PROVIDERS = {"openai": OpenAIImageProvider}


def get_image_provider(settings: Settings) -> ImageProvider:
    adapter = PROVIDERS.get(settings.image_provider)
    if adapter is None or not settings.image_model.strip() or not settings.openai_api_key.get_secret_value().strip():
        raise ServiceError(503, "Food illustrations aren't configured yet. You can still browse the menu.")
    return adapter(settings)
