"""LLM API call wrapper with retry, timeout, streaming support, and token tracking."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI


class LLMGateway:
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        token_tracker: Optional[object] = None,  # TokenTracker
        task_name: str = "",
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client: AsyncOpenAI | None = None
        self._token_tracker = token_tracker
        self._task_name = task_name

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
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=stream,
                        timeout=10,
                    ),
                    timeout=15,
                )
                if stream:
                    return self._collect_stream(response)
                usage = getattr(response, "usage", None)
                if usage and self._token_tracker:
                    self._token_tracker.record(
                        model=self.model,
                        prompt_tokens=usage.prompt_tokens,
                        completion_tokens=usage.completion_tokens,
                        task=self._task_name,
                    )
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(1)
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
