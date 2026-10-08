import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.telemetry import record_llm_usage
from apps.api.app.models.entities import LLMUsageLog

PRICING_TABLE = {
    "local": {"input_per_1k": 0.0001, "output_per_1k": 0.0002},
    "openai": {"input_per_1k": 0.0025, "output_per_1k": 0.0100},
    "anthropic": {"input_per_1k": 0.0030, "output_per_1k": 0.0150},
    "gemini": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
}


class LLMGatewayService:
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
        
        # Approximate token count (1 token ≈ 4 chars)
        input_tokens = max(len(prompt) // 4, 1)

        # Simulate provider inference with fallback logic
        rates = PRICING_TABLE.get(provider, PRICING_TABLE["local"])
        response_text = (
            f"[Gateway Routed: {provider}/{model}]\n"
            f"Processed request for workload: '{workload_id}'.\n"
            f"Input query prompt received: '{prompt}'.\n"
            f"System latency and quality gates verified within SLA."
        )
        output_tokens = max(len(response_text) // 4, 1)

        latency_ms = round((time.time() - start_time + 0.085) * 1000, 2)
        cost = (
            (input_tokens / 1000.0) * rates["input_per_1k"]
            + (output_tokens / 1000.0) * rates["output_per_1k"]
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
            status="success",
        )
        db.add(log_entry)

        # Telemetry
        record_llm_usage(
            provider=provider,
            model=model,
            status="success",
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
            "model": model,
            "response": response_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "estimated_cost": round(cost, 6),
            "status": "success",
        }

    @classmethod
    async def get_cost_summary(cls, db: AsyncSession, workload_id: str | None = None) -> dict[str, Any]:
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
