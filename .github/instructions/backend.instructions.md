---
applyTo: "py/apps/vin-insight/**"
---

# Backend Instructions

These instructions apply when working with files in the `py/apps/vin-insight/` directory.

## Tech Stack

- **Framework:** FastAPI
- **Language:** Python 3.11+
- **Dependency Manager:** uv
- **Linting:** Ruff
- **Testing:** pytest
- **Tracing:** OpenTelemetry -> Azure Monitor
- **Agent Orchestration:** Azure AI Foundry Agent SDK (via foundrykit library)
- **External API:** NHTSA VIN Decode API

## Critical Rules

1. **Every function MUST have:**
   - Complete type hints
   - Docstring with `:param`, `:return:`, `:raises:`
   - Error handling (try/except)
   - Structured logging via `structlog` (no `print()`)
2. **Every tool function MUST create an OpenTelemetry child span**
3. **All API contracts are Pydantic models**
4. **The Foundry Agent is the control plane** — it decides which tools to call per VIN analysis

## Tool Functions

| Tool | File | Purpose |
|------|------|---------|
| `decode_vin()` | `tools/decode_vin.py` | Decode a VIN via NHTSA vPIC API |
| `validate_vin_response()` | `tools/validate_vin.py` | Validate and extract vehicle attributes from decode result |
| `create_claim()` | `tools/create_claim.py` | Create a fleet maintenance claim when analysis warrants it |

## Function Pattern

```python
from __future__ import annotations

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def decode_vin(vin: str) -> str:
    """
    Decode a VIN via the NHTSA vPIC API.

    :param vin: 17-character Vehicle Identification Number.
    :return: JSON string with decoded vehicle attributes.
    :raises RuntimeError: If the API call fails.
    """
    with tracer.start_as_current_span("tool.decode_vin") as span:
        span.set_attribute("tool.name", "decode_vin")
        span.set_attribute("tool.args.vin", vin)
        ...
```

## File Structure

| Type | Location |
|------|----------|
| App Entry | `main.py` |
| API Routes | `api/v1/vin.py` |
| Tool Functions | `tools/` |
| Config | `core/config.py` |
| Telemetry | `core/telemetry.py` |
| System Prompt | `prompts/vin_insight_system.md` |
| Tests | `tests/` |

## Runtime Modes

| Variable | Values | Purpose |
|----------|--------|---------|
| `FOUNDRY_CREDENTIAL_MODE` | `dev` / `managed_identity` | Foundry auth mode |
| `OTEL_EXPORTER` | `console` / `aitoolkit` / `azure` | Trace export target |

## Related Documentation

See [coding-standards.md](../coding-standards.md) for detailed backend standards.
See [system-design.md](../system-design.md) for architecture.
