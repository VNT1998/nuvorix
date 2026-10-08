import threading
from collections import deque
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# --- OpenTelemetry Tracing Infrastructure ---

class RingBufferSpanExporter(SpanExporter):
    """Thread-safe ring buffer storing recent spans for real-time observability."""
    def __init__(self, maxlen: int = 200):
        self._spans: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            for s in spans:
                start_ns = s.start_time or 0
                end_ns = s.end_time or 0
                duration_ms = round((end_ns - start_ns) / 1_000_000.0, 2) if end_ns > start_ns else 0.0

                self._spans.append({
                    "name": s.name,
                    "trace_id": format(s.context.trace_id, "032x"),
                    "span_id": format(s.context.span_id, "016x"),
                    "parent_id": format(s.parent.span_id, "016x") if s.parent else None,
                    "duration_ms": duration_ms,
                    "status": s.status.status_code.name,
                    "attributes": dict(s.attributes) if s.attributes else {},
                })
        return SpanExportResult.SUCCESS

    def get_recent_spans(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._spans)

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()

    def shutdown(self) -> None:
        pass


_resource = Resource.create({
    "service.name": "nuvorix-control-plane",
    "service.version": "0.1.0",
    "deployment.environment": "development",
})
_provider = TracerProvider(resource=_resource)
_span_exporter = RingBufferSpanExporter(maxlen=200)
_provider.add_span_processor(SimpleSpanProcessor(_span_exporter))
trace.set_tracer_provider(_provider)

tracer: trace.Tracer = trace.get_tracer("nuvorix-control-plane", "0.1.0")


def get_tracer() -> trace.Tracer:
    return tracer


def get_recent_spans() -> list[dict[str, Any]]:
    """Retrieve recently captured distributed trace spans."""
    return _span_exporter.get_recent_spans()


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None):
    """Context manager to create and record an OpenTelemetry trace span."""
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                if v is not None:
                    span.set_attribute(k, str(v) if isinstance(v, (dict, list, bool)) else v)
        yield span


# --- Prometheus Metrics ---

# HTTP Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "nuvorix_http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "nuvorix_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)
ERRORS_TOTAL = Counter(
    "nuvorix_errors_total",
    "Total count of system errors",
    ["error_type", "component"],
)

# LLM Gateway Metrics
LLM_REQUESTS_TOTAL = Counter(
    "nuvorix_llm_requests_total",
    "Total count of LLM requests handled by Gateway",
    ["provider", "model", "status"],
)
LLM_LATENCY_SECONDS = Histogram(
    "nuvorix_llm_latency_seconds",
    "Latency of LLM calls in seconds",
    ["provider", "model"],
)
LLM_INPUT_TOKENS_TOTAL = Counter(
    "nuvorix_llm_input_tokens_total",
    "Total count of LLM input tokens",
    ["provider", "model"],
)
LLM_OUTPUT_TOKENS_TOTAL = Counter(
    "nuvorix_llm_output_tokens_total",
    "Total count of LLM output tokens",
    ["provider", "model"],
)
LLM_COST_TOTAL = Counter(
    "nuvorix_llm_cost_total",
    "Estimated or actual cost of LLM requests in USD",
    ["provider", "model"],
)

# RAG & Retrieval Metrics
RETRIEVAL_LATENCY_SECONDS = Histogram(
    "nuvorix_retrieval_latency_seconds",
    "Latency of document retrieval queries in seconds",
    ["knowledge_base_id"],
)

# Agent & Tool Call Metrics
TOOL_CALLS_TOTAL = Counter(
    "nuvorix_tool_calls_total",
    "Total tool invocations by agents",
    ["tool_name", "status"],
)
TOOL_FAILURES_TOTAL = Counter(
    "nuvorix_tool_failures_total",
    "Total failed tool calls",
    ["tool_name", "reason"],
)

# Platform Operations Metrics
EVALUATION_RUNS_TOTAL = Counter(
    "nuvorix_evaluation_runs_total",
    "Total evaluation runs executed",
    ["workload_id", "decision"],
)
DEPLOYMENT_TOTAL = Counter(
    "nuvorix_deployment_total",
    "Total workload deployments executed",
    ["environment", "strategy", "status"],
)
INCIDENTS_TOTAL = Counter(
    "nuvorix_incidents_total",
    "Total platform incidents recorded",
    ["severity", "status"],
)
ACTIVE_WORKLOADS_GAUGE = Gauge(
    "nuvorix_active_workloads",
    "Count of currently active workloads",
    ["type"],
)


def get_metrics_payload() -> bytes:
    """Export Prometheus format metrics."""
    return generate_latest()


def record_http_request(method: str, endpoint: str, status_code: int, duration_sec: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration_sec)


def record_llm_usage(
    provider: str,
    model: str,
    status: str,
    input_tokens: int,
    output_tokens: int,
    latency_sec: float,
    cost: float,
) -> None:
    LLM_REQUESTS_TOTAL.labels(provider=provider, model=model, status=status).inc()
    LLM_LATENCY_SECONDS.labels(provider=provider, model=model).observe(latency_sec)
    LLM_INPUT_TOKENS_TOTAL.labels(provider=provider, model=model).inc(input_tokens)
    LLM_OUTPUT_TOKENS_TOTAL.labels(provider=provider, model=model).inc(output_tokens)
    LLM_COST_TOTAL.labels(provider=provider, model=model).inc(cost)

