import httpx
from app.core.config import Settings
from app.schemas.document import PreparedDocument
from app.schemas.explanation import DishSource
from app.services.ai.base import AIProvider, ProviderResult, ProviderError
from app.services.ai.http import post_json


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.model = settings.menu_ai_model
        self.transport = transport

    async def extract_menu(self, document: PreparedDocument, schema: dict, instructions: str) -> ProviderResult:
        content = []
        for page in document.pages:
            content.append({"type": "input_text", "text": f"Source page {page.page_number}"})
            if page.kind == "text":
                content.append({"type": "input_text", "text": page.text})
            else:
                content.append({"type": "input_image", "image_url": f"data:{page.media_type};base64,{page.data_base64}"})
                if page.extracted_text:
                    content.append({"type": "input_text", "text": page.extracted_text})
        return await self._request(content, schema, instructions, "menu_extraction", self.settings.menu_ai_max_output_tokens)

    async def generate_description(self, source: DishSource, language: str, schema: dict, instructions: str) -> ProviderResult:
        content = [{"type": "input_text", "text": source.model_dump_json()}]
        return await self._request(content, schema, instructions, "dish_explanation", 2000)

    async def interpret_search(self, query: str, schema: dict, instructions: str) -> ProviderResult:
        content = [{"type": "input_text", "text": query}]
        return await self._request(content, schema, instructions, "search_intent", 2000)

    async def _request(self, content: list[dict], schema: dict, instructions: str, format_name: str, max_tokens: int) -> ProviderResult:
        payload = {"model": self.model, "store": False, "instructions": instructions,
                   "input": [{"role": "user", "content": content}], "max_output_tokens": max_tokens,
                   "text": {"format": {"type": "json_schema", "name": format_name, "strict": True, "schema": schema}}}
        async with httpx.AsyncClient(timeout=self.settings.menu_ai_timeout_seconds, transport=self.transport) as client:
            body = await post_json(client, "https://api.openai.com/v1/responses", {"Authorization": f"Bearer {self.settings.openai_api_key.get_secret_value()}"}, payload)
        try:
            blocks = [block for item in body.get("output", []) if item.get("type") == "message" for block in item.get("content", [])]
            if any(block.get("type") == "refusal" for block in blocks):
                raise ProviderError("This menu couldn't be understood. Please try a different file.", 422)
            if body.get("status") != "completed":
                raise ProviderError("The menu response was incomplete. Please try a smaller menu.", 422)
            text = "".join(block["text"] for block in blocks if block.get("type") == "output_text")
            usage = body.get("usage") or {}
            return ProviderResult(text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)))
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderError("The menu processing service returned an unreadable response.") from None
