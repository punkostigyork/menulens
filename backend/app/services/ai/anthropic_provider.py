import httpx
from app.core.config import Settings
from app.schemas.document import PreparedDocument
from app.schemas.explanation import DishSource
from app.services.ai.base import AIProvider, ProviderError, ProviderResult
from app.services.ai.http import post_json


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.model = settings.menu_ai_model
        self.transport = transport

    async def extract_menu(self, document: PreparedDocument, schema: dict, instructions: str) -> ProviderResult:
        content = []
        for page in document.pages:
            content.append({"type": "text", "text": f"Source page {page.page_number}"})
            if page.kind == "text":
                content.append({"type": "text", "text": page.text})
            else:
                content.append({"type": "image", "source": {"type": "base64", "media_type": page.media_type, "data": page.data_base64}})
                if page.extracted_text:
                    content.append({"type": "text", "text": page.extracted_text})
        return await self._request(content, schema, instructions, "menu_extraction", self.settings.menu_ai_max_output_tokens)

    async def generate_description(self, source: DishSource, language: str, schema: dict, instructions: str) -> ProviderResult:
        content = [{"type": "text", "text": source.model_dump_json()}]
        return await self._request(content, schema, instructions, "dish_explanation", 2000)

    async def interpret_search(self, query: str, schema: dict, instructions: str) -> ProviderResult:
        content = [{"type": "text", "text": query}]
        return await self._request(content, schema, instructions, "search_intent", 2000)

    async def _request(self, content: list[dict], schema: dict, instructions: str, format_name: str, max_tokens: int) -> ProviderResult:
        payload = {"model": self.model, "max_tokens": max_tokens, "system": instructions,
                   "messages": [{"role": "user", "content": content}], "output_config": {"format": {"type": "json_schema", "schema": schema}}}
        async with httpx.AsyncClient(timeout=self.settings.menu_ai_timeout_seconds, transport=self.transport) as client:
            body = await post_json(client, "https://api.anthropic.com/v1/messages", {"x-api-key": self.settings.anthropic_api_key.get_secret_value(), "anthropic-version": "2023-06-01"}, payload)
        try:
            if body.get("stop_reason") != "end_turn":
                raise ProviderError("The menu response was incomplete or declined. Please try a smaller or clearer menu.", 422)
            text = "".join(block["text"] for block in body.get("content", []) if block.get("type") == "text")
            usage = body.get("usage") or {}
            return ProviderResult(text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderError("The menu processing service returned an unreadable response.") from None
