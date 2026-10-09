import asyncio
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import record_llm_usage
from apps.api.app.models.entities import LLMUsageLog

logger = logging.getLogger(__name__)

PRICING_TABLE = {
    "local": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
    "openai": {"input_per_1k": 0.0025, "output_per_1k": 0.0100},
    "anthropic": {"input_per_1k": 0.0030, "output_per_1k": 0.0150},
    "gemini": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
    "ollama": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
}


def calculate_token_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    rates = PRICING_TABLE.get(provider, PRICING_TABLE["local"])
    cost = (input_tokens / 1000.0) * rates["input_per_1k"] + (output_tokens / 1000.0) * rates[
        "output_per_1k"
    ]
    return round(cost, 6)


class ProviderResult(BaseModel):
    id: str | None = None
    provider: str
    requested_provider: str
    actual_provider: str
    model: str
    response: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    estimated_cost: float
    status: str
    usage_source: str
    cost_mode: str
    pricing_source: str = "centralized_catalog"
    fallback_reason: str | None = None


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> tuple[str, int, int, str]:
        """Returns tuple of (completion_text, input_tokens, output_tokens, usage_source)."""

    @abstractmethod
    def stream_generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Yields completion chunks as they are generated."""


class OpenAICompatibleProvider(BaseLLMProvider):
    """Real HTTP client supporting any OpenAI-compatible API (OpenAI, Groq, Ollama, vLLM)."""

    def __init__(
        self, base_url: str | None = None, api_key: str | None = None, timeout_sec: float = 8.0
    ):
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("LOCAL_LLM_URL")
            or "https://api.openai.com/v1"
        )
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.timeout = timeout_sec

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> tuple[str, int, int, str]:
        if (
            not self.api_key
            and "localhost" not in self.base_url
            and "127.0.0.1" not in self.base_url
        ):
            raise ValueError("No API key configured for remote provider.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions", headers=headers, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            text = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            has_provider_usage = "prompt_tokens" in usage and "completion_tokens" in usage
            in_tok = usage.get("prompt_tokens", max(len(prompt) // 4, 1))
            out_tok = usage.get("completion_tokens", max(len(text) // 4, 1))
            usage_source = "provider" if has_provider_usage else "estimated"
            return text, in_tok, out_tok, usage_source

    async def stream_generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        text, _, _, _ = await self.generate(model, prompt, max_tokens, temperature)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.01)


class LocalDeterministicProvider(BaseLLMProvider):
    """Local deterministic provider for offline operations and testing."""

    async def generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> tuple[str, int, int, str]:
        input_tokens = max(len(prompt.split()) * 2, 1)

        # Generate contextual response based on prompt intent
        p_lower = prompt.lower()
        if "architecture" in p_lower or "invariant" in p_lower:
            text = (
                "Nuvorix Architecture Invariants:\n"
                "1. All workloads require quality gate validation (ALLOW/BLOCK) prior to promotion.\n"
                "2. Distributed traces are captured across all control plane operations.\n"
                "3. Invariant breaches immediately trigger automated rollback to the last verified active deployment."
            )
        elif "deploy" in p_lower or "rollback" in p_lower:
            text = "Deployment status check complete: Rollout verification passed. Safe to proceed with progression."
        elif "diagnostic" in p_lower or "health" in p_lower:
            text = "Diagnostics evaluated: Core database pools, vector indices, and message buffers are healthy."
        else:
            text = f"Nuvorix Gateway [{model}]: Processed request successfully under verified platform SLOs."

        output_tokens = max(len(text.split()) * 2, 1)
        return text, input_tokens, output_tokens, "estimated"

    async def stream_generate(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        text, _, _, _ = await self.generate(model, prompt, max_tokens, temperature)
        words = text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.01)


class LLMGatewayService:
    _remote_provider: BaseLLMProvider = OpenAICompatibleProvider()
    _local_provider: BaseLLMProvider = LocalDeterministicProvider()

    @classmethod
    async def chat_completion(
        cls,
        db: AsyncSession,
        workload_id: str,
        prompt: str,
        provider: str = "local",
        model: str = "llama-3-8b-instruct",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        start_time = time.time()
        status = "success"
        actual_provider = "local_demo_provider" if provider == "local" else provider
        usage_source = "estimated"
        fallback_reason = None

        # Route through provider abstraction with fallback
        response_text = ""
        input_tokens = 0
        output_tokens = 0

        if provider in ["openai", "anthropic", "gemini", "ollama"]:
            try:
                (
                    response_text,
                    input_tokens,
                    output_tokens,
                    usage_source,
                ) = await cls._remote_provider.generate(
                    model=model,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                actual_provider = "openai_compatible"
            except Exception as e:
                from apps.api.app.core.config import settings

                if settings.ENVIRONMENT.lower() == "production":
                    logger.error(
                        "Remote provider '%s' failed in production: %s. Silent fallback is prohibited.",
                        provider,
                        e,
                    )
                    raise ValueError(
                        f"Remote LLM provider '{provider}' request failed: {e}. "
                        "Fallback to deterministic local demo provider is disabled in production."
                    ) from e
                logger.warning(
                    "Remote provider '%s' failed or unconfigured (%s). Falling back to local demo provider.",
                    provider,
                    e,
                )
                status = "fallback"
                fallback_reason = str(e)
                actual_provider = "local_demo_provider"
                (
                    response_text,
                    input_tokens,
                    output_tokens,
                    usage_source,
                ) = await cls._local_provider.generate(
                    model=f"local-{model}",
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
        else:
            actual_provider = "local_demo_provider"
            (
                response_text,
                input_tokens,
                output_tokens,
                usage_source,
            ) = await cls._local_provider.generate(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

        latency_ms = round((time.time() - start_time) * 1000, 2)
        cost = calculate_token_cost(provider, model, input_tokens, output_tokens)
        cost_mode = (
            "provider_reported"
            if (
                status == "success"
                and actual_provider == "openai_compatible"
                and usage_source == "provider"
            )
            else "estimated_local"
        )

        # Log into Database
        log_entry = LLMUsageLog(
            workload_id=workload_id,
            provider=provider,
            model=model,
            prompt=prompt,
            completion=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            estimated_cost=round(cost, 6),
            cost_mode=cost_mode,
            usage_source=usage_source,
            status=status,
        )
        db.add(log_entry)

        # Telemetry
        record_llm_usage(
            provider=provider,
            model=model,
            status=status,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_sec=latency_ms / 1000.0,
            cost=cost,
        )

        await db.commit()
        await db.refresh(log_entry)

        return {
            "id": log_entry.id,
            "provider": provider,
            "requested_provider": provider,
            "actual_provider": actual_provider,
            "model": model,
            "response": response_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "estimated_cost": round(cost, 6),
            "status": status,
            "usage_source": usage_source,
            "cost_mode": cost_mode,
            "pricing_source": "centralized_catalog",
            "fallback_reason": fallback_reason,
        }

    @classmethod
    async def get_cost_summary(
        cls, db: AsyncSession, workload_id: str | None = None
    ) -> dict[str, Any]:
        query = select(LLMUsageLog)
        if workload_id:
            query = query.where(LLMUsageLog.workload_id == workload_id)

        res = await db.execute(query)
        logs = res.scalars().all()

        total_cost = 0.0
        total_in = 0
        total_out = 0
        by_model: dict[str, float] = {}
        by_provider: dict[str, float] = {}
        by_workload: dict[str, float] = {}

        for log in logs:
            c = log.estimated_cost or 0.0
            total_cost += c
            total_in += log.input_tokens or 0
            total_out += log.output_tokens or 0

            by_model[log.model] = round(by_model.get(log.model, 0.0) + c, 5)
            by_provider[log.provider] = round(by_provider.get(log.provider, 0.0) + c, 5)
            by_workload[log.workload_id] = round(by_workload.get(log.workload_id, 0.0) + c, 5)

        return {
            "total_cost": round(total_cost, 4),
            "total_requests": len(logs),
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "breakdown_by_model": by_model,
            "breakdown_by_provider": by_provider,
            "breakdown_by_workload": by_workload,
        }

    @classmethod
    async def stream_chat_completion(
        cls,
        db: AsyncSession,
        workload_id: str,
        prompt: str,
        provider: str = "local",
        model: str = "llama-3-8b-instruct",
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        full_text: list[str] = []

        chosen_provider = (
            cls._remote_provider
            if provider in ["openai", "anthropic", "gemini", "ollama"]
            else cls._local_provider
        )

        try:
            async for chunk in chosen_provider.stream_generate(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                full_text.append(chunk)
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"
        except Exception as e:
            from apps.api.app.core.config import settings

            if settings.ENVIRONMENT.lower() == "production":
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                return
            async for chunk in cls._local_provider.stream_generate(
                model=f"local-{model}",
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            ):
                full_text.append(chunk)
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"

        latency_ms = round((time.time() - start_time) * 1000, 2)
        assembled = "".join(full_text)
        in_tok = max(len(prompt.split()) * 2, 1)
        out_tok = max(len(assembled.split()) * 2, 1)
        cost = calculate_token_cost(provider, model, in_tok, out_tok)

        log_entry = LLMUsageLog(
            workload_id=workload_id,
            provider=provider,
            model=model,
            prompt=prompt,
            completion=assembled,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency_ms,
            estimated_cost=cost,
            cost_mode="estimated_local",
            usage_source="estimated",
            status="success",
        )
        db.add(log_entry)
        await db.commit()

        yield f"data: {json.dumps({'token': '', 'done': True, 'cost': cost, 'latency_ms': latency_ms, 'input_tokens': in_tok, 'output_tokens': out_tok})}\n\n"
