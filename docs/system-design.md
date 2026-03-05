# System Design — LoanFlow AI

## Overview

LoanFlow AI provides an AI-assisted lending workflow centered on mortgage origination with a companion servicing experience.

The current implementation focuses on origination:

- conversational intake
- document upload and quality validation
- applicant data extraction
- application summary generation
- approval-letter generation
- structured audit logging

This document is the detailed architecture reference for developers. The quick project entrypoint lives in [README.md](../README.md).

## Runtime Components

| Component | Path | Role |
|---|---|---|
| API service | `py/apps/loan-origination` | FastAPI endpoint and agent orchestration |
| Foundry wrapper | `py/libs/foundrykit` | `FoundryClient`, `AgentManager`, `ToolRegistry` |
| Prompt tools | `py/apps/loan-origination/tools` | `validate_document_quality`, `extract_document_fields`, `assemble_application`, `generate_approval_letter`, `log_audit_event` |
| Frontend SPA | `ts/apps/loan-ui` | Applicant/broker chat interface |
| Infra | `infra` | Azure deployment resources |

## API Surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness/readiness |
| `POST` | `/api/v1/loan/stream` | Stream conversational origination assistant over SSE |
| `POST` | `/api/v1/loan/upload` | Upload and register a document |
| `GET` | `/api/v1/loan/{id}` | Read application details |
| `GET` | `/api/v1/loan/{id}/audit` | Read audit events |
| `GET` | `/api/v1/loan/{id}/documents` | Read uploaded/extracted documents |

## End-to-End Request Flow (Streaming)

1. Frontend sends `POST /api/v1/loan/stream` with `{ conversation_id, message_id, message, history, application_id?, document_context? }`.
2. Backend creates a temporary Prompt Agent with the loan-origination system prompt and registered tools.
3. Backend creates an agent thread and appends the user message.
5. `AgentManager.run_agent_stream()` starts `runs.stream(...)`.
6. Agent triggers `validate_document_quality(...)` for uploaded files.
7. Agent triggers `extract_document_fields(...)` and assembles application state with `assemble_application(...)`.
8. Agent emits markdown response chunks as text deltas; backend forwards them as SSE `delta` events.
9. Agent can call `generate_approval_letter(...)` and `log_audit_event(...)`.
10. Backend persists application/conversation artifacts and sends SSE `done`.
11. Temporary agent is deleted via context manager cleanup.

## Foundry Integration Details

### FoundryClient

- Singleton around `AIProjectClient`
- Supports `dev` credentials (`DefaultAzureCredential`) and `managed_identity`
- Model deployment is selected via configuration (`FOUNDRY_MODEL_DEPLOYMENT_NAME`)

### AgentManager

- Creates/deletes agents
- Creates threads and posts messages
- Supports sync run (`run_agent`) and streaming run (`run_agent_stream`)
- Uses retry logic for throttling (`429`)

Important implementation detail:

- After `create_agent(toolset=...)`, `AgentManager` registers function callables on the SDK runs object so local Python tool execution works during streaming.

### ToolRegistry

- Wraps plain Python functions into a `ToolSet`
- Preserves type hints/docstrings for tool schema generation
- Automatically traces tool invocation spans with OpenTelemetry
- Supports MCP tools via `add_mcp_tool()` for remote server integration

### MCP (Model Context Protocol) Support

- Optional integration with remote MCP servers via `McpTool`
- MCP tools are server-side — Azure Agent Service calls the remote server directly
- `create_mcp_tool()` factory with headers, approval mode, and tool filtering
- `McpRunHandler` for auto-approval during `create_and_process()`
- Streaming auto-approval via `mcp_tools` parameter in `run_agent_stream()`
- See [MCP Guide](mcp-guide.md) for full documentation

## Storage Model

Two storage implementations behind one interface:

- `InMemoryStorage` for local development
- `CosmosStorage` for production

Data entities:

- `LoanApplication` → `applications` container (partition key `/application_id`)
- `DocumentRecord` → `documents` container (partition key `/application_id`)
- `Conversation` → `conversations` container (partition key `/conversation_id`)
- `AuditEvent` → `audit_events` container (partition key `/application_id`)

## Architecture Decisions

### 1) SSE for Response Streaming

Chosen to support long-form responses with incremental rendering and lower complexity than WebSockets for this one-way stream use case.

### 2) Temporary Agent per Request

Chosen for strict request isolation, deterministic cleanup, and to avoid stale state across conversations.

### 3) Tool-Driven Agent Workflow

Chosen to keep document validation/extraction deterministic while still using model reasoning for conversational guidance and summaries.

### 4) Foundry Wrapper Library (`foundrykit`)

Chosen to isolate Azure SDK lifecycle, retries, and streaming/event handling from business endpoints.

### 5) Dual Storage Mode

Chosen to keep local development zero-dependency (`inmemory`) while preserving production-grade persistence (`cosmos`).

### 6) New AI Foundry Provisioning Model

Chosen to align with current Agents API compatibility (`CognitiveServices/accounts` + child projects) instead of legacy hub-based resources.

### 7) MCP (Model Context Protocol) Support

Chosen to enable the agent to call remote tool servers (MCP servers) for external data enrichment — lending regulations, rate sheets, credit checks — without embedding that logic locally. MCP is opt-in via environment variables and backward-compatible with function-tools-only mode.


## Related Docs

- Setup: [dev-setup.md](dev-setup.md)
- Local testing: [local-testing.md](local-testing.md)
- Security: [security-design.md](security-design.md)
- Network: [network-design.md](network-design.md)
- Processors: [processors-design.md](processors-design.md)
- MCP integration: [mcp-guide.md](mcp-guide.md)

