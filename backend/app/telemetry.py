"""
Mall Operations Brain — OpenTelemetry Instrumentation Module

Initializes the full OTel stack: traces + metrics exported to Elastic APM
via OTLP/HTTP. Provides a shared tracer, meter, and pre-registered custom
metrics for agent health and business impact dashboards.

If OTEL_EXPORTER_OTLP_ENDPOINT is not set, falls back to console exporters
so traces/metrics are printed to stdout (useful for local dev).
"""

import os
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader,
    ConsoleMetricExporter,
)
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)

# ─── Module-Level Singletons ─────────────────────────────────────────────────
# These are populated by init_telemetry() and imported by other modules.

tracer: trace.Tracer = trace.get_tracer("mall_operations_brain")
meter: metrics.Meter = metrics.get_meter("mall_operations_brain")

_initialized = False


class ObservabilityMetrics:
    """Pre-registered custom metrics for agent health and business impact."""

    def __init__(self, m: metrics.Meter):
        # ── Agent Health Metrics ──────────────────────────────────────────
        self.tokens_consumed = m.create_counter(
            name="agent.tokens.consumed",
            description="Total tokens consumed by the agent per request",
            unit="tokens",
        )
        self.tool_calls = m.create_counter(
            name="agent.tool.calls",
            description="Number of tool invocations by the agent",
            unit="calls",
        )
        self.reasoning_duration = m.create_histogram(
            name="agent.reasoning.duration_ms",
            description="Duration of agent reasoning/thinking phases",
            unit="ms",
        )
        self.tool_duration = m.create_histogram(
            name="agent.tool.duration_ms",
            description="Duration of individual tool executions",
            unit="ms",
        )
        self.esql_queries = m.create_counter(
            name="agent.esql.queries",
            description="Number of ES|QL queries executed",
            unit="queries",
        )
        self.session_count = m.create_counter(
            name="agent.sessions.total",
            description="Total number of agent sessions started",
            unit="sessions",
        )

        # ── Business Impact Metrics ───────────────────────────────────────
        self.coupon_activations = m.create_counter(
            name="coupon.activations",
            description="Number of customer coupons generated and activated",
            unit="activations",
        )
        self.pulse_workflow_runs = m.create_counter(
            name="pulse.workflow.runs",
            description="Number of autonomous pulse workflow feed fetches observed",
            unit="runs",
        )
        self.search_queries = m.create_counter(
            name="search.hybrid.queries",
            description="Number of hybrid search queries executed",
            unit="queries",
        )


# Module-level metrics container — populated after init
obs_metrics: ObservabilityMetrics = None  # type: ignore


def init_telemetry():
    """
    Initialize the OpenTelemetry tracing and metrics stack.

    Exports to Elastic APM via OTLP/HTTP if OTEL_EXPORTER_OTLP_ENDPOINT is set.
    Falls back to console exporters otherwise (local dev mode).
    """
    global tracer, meter, obs_metrics, _initialized

    if _initialized:
        return

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    service_name = os.getenv("OTEL_SERVICE_NAME", "mall-operations-brain")

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "2.0.0",
        "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "hackathon"),
    })

    # ── Traces ────────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            otlp_headers = _parse_otlp_headers()
            span_exporter = OTLPSpanExporter(
                endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces",
                headers=otlp_headers,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
            logger.info(f"[OTEL] Trace exporter configured → {otlp_endpoint}/v1/traces")
        except Exception as e:
            logger.warning(f"[OTEL] Failed to configure OTLP trace exporter: {e}. Falling back to console.")
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info("[OTEL] No OTLP endpoint configured. Using console trace exporter.")

    trace.set_tracer_provider(tracer_provider)
    tracer = trace.get_tracer("mall_operations_brain", "2.0.0")

    # ── Metrics ───────────────────────────────────────────────────────────
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
            otlp_headers = _parse_otlp_headers()
            metric_exporter = OTLPMetricExporter(
                endpoint=f"{otlp_endpoint.rstrip('/')}/v1/metrics",
                headers=otlp_headers,
            )
            metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15000)
            logger.info(f"[OTEL] Metric exporter configured → {otlp_endpoint}/v1/metrics")
        except Exception as e:
            logger.warning(f"[OTEL] Failed to configure OTLP metric exporter: {e}. Falling back to console.")
            metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=30000)
    else:
        metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=30000)
        logger.info("[OTEL] No OTLP endpoint configured. Using console metric exporter.")

    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("mall_operations_brain", "2.0.0")

    # ── Register Custom Metrics ───────────────────────────────────────────
    obs_metrics = ObservabilityMetrics(meter)

    # ── Auto-Instrument FastAPI ───────────────────────────────────────────
    # This will be called after the FastAPI app is created, so we defer
    # the actual instrumentation to instrument_app().

    _initialized = True
    logger.info("[OTEL] ✅ Telemetry stack initialized successfully.")


def instrument_app(app):
    """Auto-instrument a FastAPI application with OTel request/response tracing."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("[OTEL] ✅ FastAPI auto-instrumentation enabled.")
    except Exception as e:
        logger.warning(f"[OTEL] FastAPI instrumentation failed: {e}")


def _parse_otlp_headers() -> dict:
    """Parse OTEL_EXPORTER_OTLP_HEADERS env var into a dict."""
    raw = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
    if not raw:
        return {}
    headers = {}
    for pair in raw.split(","):
        if "=" in pair:
            key, value = pair.split("=", 1)
            headers[key.strip()] = value.strip()
    return headers
