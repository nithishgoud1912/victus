# Create backend/victus/models/ollama.py with an asynchronous OllamaClient and a local-only base URL. Its first methods are health(), list_models() and chat(). Add httpx as a runtime dependency:

# # Working directory: backend
# uv add "httpx>=0.27,<1"
# First request shape for chat():

# payload = {
#     "model": "qwen3:4b",
#     "messages": [{"role": "user", "content": "Reply with the word ready."}],
#     "stream": False,
#     "options": {"num_ctx": 4096},
# }

import asyncio
import os
from typing import AsyncIterator, Sequence, TypedDict

import httpx

from .base import ModelClient


class OllamaMessage(TypedDict):
    role: str
    content: str


class OllamaResponse(TypedDict):
    model: str
    created_at: str
    response: str
    done: bool
    


class OllamaClient(ModelClient):
    """
    An asynchronous Ollama client that talks to the local Ollama server.
    Uses http://localhost:11434 by default.
    """
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def health(self) -> dict:
        """
        Check if Ollama is reachable.
        """
        resp = await self.client.get("/api/tags")
        resp.raise_for_status()
        return resp.json()

    async def list_models(self) -> list[str]:
        """
        Return the list of available models.
        """
        resp = await self.client.get("/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json()["models"]]

    async def chat(
        self,
        model: str,
        messages: Sequence[OllamaMessage],
    ) -> AsyncIterator[str]:
        """
        Send a chat request and stream the response.
        """
        data = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        async with self.client.stream("POST", "/api/chat", json=data) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = _parse_ollama_chunk(line)
                if chunk["done"]:
                    break
                yield chunk["response"]

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        """
        Simplified generate API (wraps chat).
        """
        messages: list[OllamaMessage] = [{"role": "user", "content": prompt}]
        async for chunk in self.chat(model, messages):
            yield chunk


def _parse_ollama_chunk(line: str) -> OllamaResponse:
    """
    Parse one line of JSON from the Ollama streaming response.
    """
    return httpx.parse_json(line)


# In production, you should probably use a service registry or config
def create_default_ollama_client() -> OllamaClient:
    """Returns a client configured for the environment (localhost by default)."""
    return OllamaClient(
        base_url=os.getenv("VICTUS_OLLAMA_URL", "http://localhost:11434")
    )


# Minimal example usage for quick testing
async def demo() -> None:
    """
    Quick demo: show models, then send a simple prompt.
    """
    client = OllamaClient()
    try:
        print("Health:", await client.health())
        models = await client.list_models()
        print("Available models:", models)
        if not models:
            print("No models found. Did you run 'ollama pull qwen3:4b'?")
            return

        model = models[0]
        print(f"\nSending prompt to {model}...")

        async for chunk in client.chat(
            model,
            [{"role": "user", "content": "Say 'Hello' in 3 words"}],
        ):
            print(chunk, end="", flush=True)
        print()
    except httpx.RequestException as e:
        print("Ollama connection error:", e)
    finally:
        await client.client.aclose()


if __name__ == "__main__":
    asyncio.run(demo())