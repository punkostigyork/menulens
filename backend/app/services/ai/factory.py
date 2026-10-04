from app.core.config import Settings
from app.core.errors import ServiceError
from app.services.ai.base import AIProvider
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.anthropic_provider import AnthropicProvider

PROVIDERS = {"openai": OpenAIProvider, "anthropic": AnthropicProvider}


def get_provider(settings: Settings) -> AIProvider:
    provider_type = PROVIDERS.get(settings.menu_ai_provider)
    if provider_type is None:
        raise ServiceError(503, "Menu understanding isn't configured yet.")
    key = settings.openai_api_key if settings.menu_ai_provider == "openai" else settings.anthropic_api_key
    if not key.get_secret_value().strip() or not settings.menu_ai_model.strip():
        raise ServiceError(503, "Menu understanding isn't configured yet.")
    return provider_type(settings)
