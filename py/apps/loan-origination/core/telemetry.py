"""OpenTelemetry TracerProvider configuration for Loan Origination.

Supports three exporter modes via ``OTEL_EXPORTER``:

- ``console``   — prints spans to stdout (default for local dev).
- ``aitoolkit`` — OTLP HTTP to ``localhost:4318`` (VS Code AI Toolkit).
- ``azure``     — Azure Monitor exporter to Application Insights.
"""

from __future__ import annotations

import os

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

logger = structlog.get_logger(__name__)

_RESOURCE = Resource.create({"service.name": "loan-origination"})
_tracer_provider: TracerProvider | None = None


def configure_tracing(mode: str) -> TracerProvider:
    """Configure the global ``TracerProvider`` based on the exporter mode.

    :param mode: One of ``"console"``, ``"aitoolkit"``, or ``"azure"``.
    :return: The configured ``TracerProvider``.
    :raises ValueError: If *mode* is not recognised.
    """
    global _tracer_provider

    provider = TracerProvider(resource=_RESOURCE)

    if mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    elif mode == "aitoolkit":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "http://localhost:4318",
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
        )

    elif mode == "azure":
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

        conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        if not conn_str:
            logger.warning("azure_monitor_no_connection_string")
        exporter = AzureMonitorTraceExporter(connection_string=conn_str)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    else:
        raise ValueError(f"Unknown OTEL_EXPORTER mode: {mode!r}")

    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    logger.info("tracing_configured", mode=mode)
    return provider


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer scoped to *name*.

    :param name: Logical tracer name (e.g. ``"loan.tools"``).
    :return: An OpenTelemetry ``Tracer``.
    """
    return trace.get_tracer(name)


def instrument_fastapi(app: FastAPI) -> None:
    """Attach the OpenTelemetry ASGI middleware to a FastAPI app.

    :param app: The FastAPI application instance.
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    logger.info("fastapi_instrumented")
