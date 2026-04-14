"""LLM API call wrapper with retry, timeout, and streaming support."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from openai import AsyncOpenAI


class LLMGateway:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
    ) -> str:
        client = self._get_client()
        for attempt in range(5):
            try:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                )
                if stream:
                    return self._collect_stream(response)
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt == 4:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def _collect_stream(self, response) -> str:
        parts = []
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                parts.append(delta.content)
        return "".join(parts)
