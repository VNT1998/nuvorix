# ADR 0001: Hybrid LLM Provider Gateway and FinOps Cost Metering

## Status
Accepted

## Context
GenAI platform applications require integration with heterogeneous commercial LLM APIs (OpenAI, Anthropic, Gemini) as well as on-premise inference engines (Ollama, vLLM). Directly embedding provider SDKs inside application route handlers leads to vendor lock-in, unmetered token consumption, and catastrophic failures when external APIs suffer rate limits or outages.

## Decision
1. Implement a unified `LLMGatewayService` backed by the `BaseLLMProvider` abstraction.
2. Centralize token pricing in a shared catalog (`calculate_token_cost`) with explicit accounting of prompt tokens, completion tokens, latency, and costs recorded in `LLMUsageLog`.
3. Provide Server-Sent Events (SSE) streaming (`/gateway/chat/stream`) to enable real-time UI token rendering and operator abort control (`AbortController`).
4. Enforce fail-closed error handling in production: if an external commercial provider fails, the platform raises an explicit exception rather than silently substituting mock responses. In development environments, safe deterministic fallback is preserved for offline productivity.

## Consequences
- **Positive**: Complete portability across model vendors; real-time FinOps cost tracking by organization, workload, and model; predictable offline developer workflow.
- **Negative**: Requires maintaining token pricing tables across provider changes.
