# Tracing Instructions -- Contoso Conversation Router

> **Detailed tracing guidance for coding agents.**
> For a quick summary, see the "Tracing" section in `copilot-instructions.md`.
> For a working hands-on example, run `.github/samples/lab9b_aitk_tracing.ipynb`.

---

## Local vs Azure: Two Exporter Modes

Tracing uses OpenTelemetry in both environments. The only difference is **where spans are sent**.

| | Local Development | Azure Deployment |
|---|---|---|
| **Exporter** | OTLP HTTP to `localhost:4318` (AI Toolkit) | Azure Monitor Exporter to Application Insights |
| **Config** | `OTEL_EXPORTER=console` or `aitoolkit` | `OTEL_EXPORTER=azure` |
| **Viewer** | VS Code AI Toolkit sidebar | Azure Portal > App Insights > Transaction Search |
| **Retention** | Session only | 90 days (configurable) |
| **LLM content** | Captured (dev only) | **Never capture** (PII risk) |

---

## TracerProvider Setup

The `telemetry.py` module must configure the exporter based on `OTEL_EXPORTER`:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "contoso-conv-router-backend"})
tracer_provider = TracerProvider(resource=resource)


def configure_tracing(mode: str) -> TracerProvider:
    """
    Configure the global TracerProvider based on OTEL_EXPORTER mode.

    :param mode: One of 'console', 'aitoolkit', or 'azure'.
    :return: Configured TracerProvider.
    """
    if mode == "console":
        tracer_provider.add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter())
        )
    elif mode == "aitoolkit":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    elif mode == "azure":
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        azure_exporter = AzureMonitorTraceExporter.from_connection_string(
            os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(azure_exporter))

    trace.set_tracer_provider(tracer_provider)
    return tracer_provider
```

---

## Required Span Hierarchy

Every `POST /api/v1/conversations` request MUST produce this trace tree:

```
conversation_request                    # Root span (FastAPI middleware)
+-- storage.read_conversation           # Load conversation history
+-- orchestrator.decide                 # LLM agent decision
|   +-- openai.chat                    # Azure OpenAI call (auto-instrumented)
|   +-- tool.call_kapa_api            # Knowledge base query (if used)
|   +-- tool.classify_intent          # Intent classification (if used)
|   +-- tool.ask_followup             # Qualifying question (if used)
|   +-- tool.handoff_sales            # Sales routing (if used)
|   +-- tool.handoff_support          # Support routing (if used)
+-- storage.write_routing_event         # Cosmos DB write
+-- storage.update_conversation         # Update conversation doc
```

### Root Span Attributes

| Attribute | Value | Example |
|-----------|-------|---------|
| `enduser.conversation_id` | From `x-conversation-id` header | `"conv_abc123"` |
| `enduser.message_id` | From `x-message-id` header | `"msg_def456"` |
| `auth.subject` | JWT `oid` or `sub` claim | `"user-guid"` |
| `routing.intent` | Detected intent | `"sales"` |
| `routing.action` | Routing action taken | `"answer_with_sales_cta"` |
| `llm.mode` | From `LLM_ORCHESTRATOR_MODE` | `"mock"` |

### Tool Span Pattern

Every tool function MUST create a child span with these attributes:

```python
from opentelemetry import trace
import json

tracer = trace.get_tracer(__name__)


async def call_kapa_api(query: str) -> KapaResponse:
    """Call knowledge base API for product/docs answers."""
    with tracer.start_as_current_span("tool.call_kapa_api") as span:
        span.set_attribute("tool.name", "call_kapa_api")
        span.set_attribute("tool.args", json.dumps({"query_length": len(query)}))

        result = await _query_kapa(query)

        span.set_attribute("tool.result", json.dumps({"answered": result.answered}))
        return result
```

**Required attributes on every tool span:**

| Attribute | Type | Purpose |
|-----------|------|---------|
| `tool.name` | string | Function name (for filtering in App Insights) |
| `tool.args` | JSON string | Input summary (never raw PII) |
| `tool.result` | JSON string | Output summary |

---

## Trace-to-Cosmos Reconciliation

Every routing event stored in Cosmos DB includes `trace_id` and `root_span_id`:

```python
from opentelemetry import trace

span = trace.get_current_span()
ctx = span.get_span_context()

event = RoutingEvent(
    id=f"route:{message_id}",
    pk=conversation_id,
    message_id=message_id,
    conversation_id=conversation_id,
    trace_id=format(ctx.trace_id, "032x"),
    root_span_id=format(ctx.span_id, "016x"),
    # ... rest of event fields
)
```

---

## LLM Content Recording

### Local Only

```bash
# In py/apps/apirouter/.env (local dev only)
AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED=true
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
```

### Production

These variables must be **absent or false**. Never capture prompt/completion text in production.

---

## Best Practices Summary

| Practice | Reason |
|----------|--------|
| Always create a child span for every tool function | Enables per-tool latency analysis |
| Set `tool.name`, `tool.args`, `tool.result` on every tool span | Consistent attribute schema |
| Store `trace_id` in Cosmos documents | Cross-reference traces and business data |
| Enable LLM content recording locally only | See prompt/completion for debugging; never in prod |
| Call `force_flush()` in tests and interactive sessions | Prevent spans from being lost |
| Never log raw PII in span attributes | Hash user IDs, omit sensitive fields |
| Use `BatchSpanProcessor` for network exporters | Avoid blocking requests |
| Instrument OpenAI SDK once at startup | Auto-creates `openai.chat` spans |
