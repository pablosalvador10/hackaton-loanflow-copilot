---
applyTo: "**/*.py"
---

# Python Instructions

These instructions apply to all Python files.

## Mandatory Function Requirements

**Every function MUST have ALL of these:**

1. Complete type hints (all parameters + return type)
2. Docstring with `:param`, `:return:`, `:raises:`
3. Error handling (try/except)
4. Structured logging via `structlog`
5. No `print()` statements -- EVER

## Docstring Format

```python
def classify_intent(
    message: str,
    history: list[Message] | None = None,
) -> IntentResult:
    """
    Classify the intent of a conversation message.

    :param message: The user's message text.
    :param history: (optional) Previous messages in the conversation.
    :return: Intent classification result with confidence score.
    :raises ClassificationError: If classification fails.
    """
```

## Logging Pattern

```python
import structlog

logger = structlog.get_logger(__name__)

# Correct: structured logging
logger.info("intent_classified", intent="sales", confidence=0.92)
logger.error("tool_failed", tool="call_kapa_api", error=str(e))
logger.exception("unexpected_error")  # Includes traceback

# Wrong: never use print
print("Something happened")  # FORBIDDEN
```

## Error Handling Pattern

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

## Type Hints

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import MyModel

# Use modern syntax
def process(data: dict[str, Any]) -> list[str]: ...
def maybe(value: str | None = None) -> str | None: ...
```

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | snake_case | `orchestrator.py` |
| Functions | snake_case | `classify_intent` |
| Classes | PascalCase | `ConversationRequest` |
| Constants | SCREAMING_SNAKE | `DEFAULT_TIMEOUT` |
| Variables | snake_case | `intent_confidence` |
