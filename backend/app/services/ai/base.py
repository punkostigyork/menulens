from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.schemas.document import PreparedDocument
from app.schemas.explanation import DishSource


@dataclass(frozen=True)
class ProviderResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AIProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def extract_menu(self, document: PreparedDocument, schema: dict, instructions: str) -> ProviderResult:
        """Return untrusted JSON and usage; validation belongs to the extractor."""
        raise NotImplementedError

    async def generate_description(self, source: DishSource, language: str, schema: dict, instructions: str) -> ProviderResult:
        """Generate untrusted description/tag JSON; adapters override this capability."""
        raise NotImplementedError


    async def interpret_search(self, query: str, schema: dict, instructions: str) -> ProviderResult:
        """Return untrusted intent JSON only; never select records or execute queries."""
        raise NotImplementedError
