# Coding Standards -- Contoso Conversation Router

This document defines the code style, conventions, and patterns for the project.

## General Principles

- **Type everything** -- TypeScript strict mode, Python type hints on all functions
- **Structured logging** -- never use `print()` or `console.log()` for operational output
- **Pydantic everywhere** -- all API contracts are Pydantic models
- **Test what matters** -- business logic, orchestration paths, API contracts
- **No secrets in code** -- environment variables only, `.env.example` for templates

---

## Frontend Standards (TypeScript / React + Vite)

### Tech Stack

| Tool | Purpose |
|------|---------|
| React + Vite | SPA framework |
| TypeScript | Language (strict mode) |
| Tailwind CSS | Styling |
| shadcn/ui | Component library (Radix-based) |
| pnpm | Package manager |
| MSAL | Entra ID authentication |

### TypeScript Rules

- **Strict mode enabled** -- no implicit any, no escape hatches
- **Path aliases** -- use `@/` for imports from `src/`
- **No `any` types** -- use `unknown` and narrow, or define proper types
- **Prefer interfaces** for object shapes; use `type` for unions/primitives

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Components | PascalCase | `ChatWindow.tsx` |
| Hooks | camelCase with `use` prefix | `useConversation.ts` |
| Utilities | camelCase | `collectSignals.ts` |
| Constants | SCREAMING_SNAKE_CASE | `API_BASE_URL` |
| Types/Interfaces | PascalCase | `ConversationRequest` |
| Files (non-components) | kebab-case | `api-client.ts` |

### Import Order

1. React imports
2. Third-party libraries
3. Internal aliases (`@/components`, `@/lib`)
4. Relative imports
5. Types (with `type` keyword)

```typescript
import { useState } from "react";
import { useMsal } from "@azure/msal-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { LocalComponent } from "./local-component";

import type { ConversationRequest } from "@/types";
```

### Component Structure

```typescript
"use client"; // Only if client-side interactivity needed

// 1. Imports (in order above)

// 2. Types/Interfaces
interface Props {
  title: string;
  className?: string;
}

// 3. Constants (if component-specific)
const ANIMATION_DURATION = 0.3;

// 4. Component
export function MyComponent({ title, className }: Props) {
  // Hooks first
  const [state, setState] = useState(false);

  // Handlers
  const handleClick = () => setState(true);

  // Render
  return (
    <div className={cn("base-styles", className)}>
      {title}
    </div>
  );
}
```

### Tailwind Class Organization

```typescript
className={cn(
  // 1. Layout
  "relative flex flex-col",
  // 2. Sizing
  "w-full p-4",
  // 3. Visual
  "bg-background rounded-lg border",
  // 4. States
  "hover:border-primary",
  // 5. Responsive
  "md:p-8 lg:flex-row",
  // 6. Conditional
  isActive && "border-primary",
  className
)}
```

### Component Rules

- Use **shadcn/ui** components -- don't create custom primitives
- Tailwind for styling -- no CSS modules or styled-components
- Keep components focused -- single responsibility
- Extract hooks for reusable stateful logic

---

## Backend Standards (Python / FastAPI)

### Tech Stack

| Tool | Purpose |
|------|---------|
| FastAPI | Web framework |
| Python 3.11+ | Language |
| uv | Dependency management |
| Pydantic v2 | Validation + schemas |
| Ruff | Linting + formatting |
| structlog | Structured logging |
| pytest | Testing |
| OpenTelemetry | Tracing |

### Function Requirements

Every function MUST have:
1. Complete type hints (all parameters + return type)
2. Docstring with `:param`, `:return:`, `:raises:`
3. Error handling (try/except for operations that can fail)
4. Structured logging (no `print()`)

```python
from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


async def route_conversation(
    request: ConversationRequest,
    storage: Storage,
) -> ConversationResponse:
    """
    Route an inbound conversation message through the orchestration pipeline.

    :param request: Incoming conversation request with user message and context.
    :param storage: Storage backend for conversation/session data.
    :return: Conversation response with bot reply and any routing actions.
    :raises OrchestrationError: If orchestration pipeline fails.
    """
    logger.info("routing_conversation", conversation_id=request.conversation_id)

    try:
        result = await _run_pipeline(request, storage)
        logger.info("routing_complete", conversation_id=request.conversation_id)
        return result
    except Exception as e:
        logger.exception("routing_failed", error=str(e))
        raise OrchestrationError("Failed to route conversation") from e
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `orchestrator.py` |
| Functions | snake_case | `classify_intent` |
| Classes | PascalCase | `ConversationRequest` |
| Constants | SCREAMING_SNAKE | `DEFAULT_TIMEOUT` |
| Variables | snake_case | `intent_confidence` |

### Logging Pattern

```python
import structlog

logger = structlog.get_logger(__name__)

# Correct: structured key-value logging
logger.info("routing_started", conversation_id=conversation_id, intent="sales")
logger.warning("low_confidence_intent", confidence=0.4, fallback="general")
logger.error("tool_failed", tool="call_kapa_api", error=str(e))

# Wrong: never use print
print("Something happened")  # FORBIDDEN
```

### Error Handling Pattern

```python
try:
    result = await risky_operation()
    logger.info("operation_success")
    return result
except SpecificError as e:
    logger.warning("known_error", error=str(e))
    raise
except Exception as e:
    logger.exception("unexpected_error", error=str(e))
    raise OperationError("Failed") from e
```

### OpenTelemetry Span Pattern

Every tool function should create a child span:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def call_kapa_api(query: str) -> KapaResponse:
    with tracer.start_as_current_span("tool.call_kapa_api") as span:
        span.set_attribute("tool.name", "call_kapa_api")
        span.set_attribute("tool.args", json.dumps({"query_length": len(query)}))
        # ... logic ...
        span.set_attribute("tool.result", json.dumps({"answered": True}))
        return result
```

### Pydantic Model Rules

- All API request/response types are Pydantic models
- Use `from __future__ import annotations` for forward refs
- Literal types for enums: `Literal["sales", "support", "general"]`
- Optional fields use `Optional[T] = None`
- Default factories via `Field(default_factory=list)`

---

## Infrastructure Standards

### Docker

- Use specific image tags (not `latest`)
- Multi-stage builds for smaller images
- Run as non-root user
- Never copy secrets into images
- Use `.dockerignore` to exclude unnecessary files

### Terraform

- Use `variables.tf` for all inputs
- Use `outputs.tf` for all outputs needed by env generation
- Tag all resources consistently
- Use a `prefix` variable for resource naming
- Private networking by default for data stores

### Environment Variables

- Use `.env.example` for templates (committed)
- Never commit actual `.env` files
- Document every variable with comments
- Use mode switches (dev/entra, inmemory/cosmos, mock/live, etc.)

---

## Git Conventions

### Commit Messages

Format: `type(scope): description`

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `infra`, `chore`

Examples:
- `feat(backend): add intent classification tool`
- `fix(frontend): handle missing UTM params`
- `infra: add Cosmos DB private endpoint`
- `docs: update system design with routing flow`

### Branch Naming

Format: `type/short-description`

Examples: `feat/conversation-api`, `fix/otel-span-attributes`, `infra/cosmos-private-endpoint`

---

## Related Documentation

- [copilot-instructions.md](./copilot-instructions.md) -- Master AI context
- [system-design.md](./system-design.md) -- Architecture overview
- [dev-setup.md](./dev-setup.md) -- Local development setup
- [LOCAL-TESTING.md](./LOCAL-TESTING.md) -- Testing practices
