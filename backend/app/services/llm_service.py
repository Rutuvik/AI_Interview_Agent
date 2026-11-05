
import ollama


class LLMService:
    """Service for interacting with the local Ollama LLM."""

    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.client = ollama.AsyncClient()


    async def generate_response(
        self,
        prompt: str,
        format: str | dict | None = None,
    ) -> str:
        """Generate a response using Ollama."""

        result = await self.client.generate(
            model=self.model,
            prompt=prompt,
            format=format,
        )

        return result["response"].strip()



# Reusable service instance
llm_service = LLMService()
