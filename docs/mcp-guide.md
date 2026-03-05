# MCP (Model Context Protocol) Integration Guide

## Overview

The **foundrykit** library supports [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools via the Azure AI Agent Service SDK (≥1.2.0b3). MCP tools are **server-side** — the Azure Agent Service calls a remote MCP server directly. Unlike local `FunctionTool` functions, there is no client-side code to execute.

This guide covers how to configure, use, and extend MCP tools in both the foundrykit library and the LoanFlow AI application.

## Prerequisites

- `azure-ai-agents >= 1.2.0b3` (pre-release; install with `--pre`)
- A remote MCP server accessible via Streamable HTTP
- Azure AI Foundry project endpoint

## Architecture

```
┌──────────────┐        ┌────────────────────┐        ┌──────────────────┐
│  Your App    │──────▶│  Azure AI Agent     │──────▶│  Remote MCP      │
│  (foundrykit)│        │  Service            │        │  Server          │
│              │◀──────│                    │◀──────│                  │
└──────────────┘        └────────────────────┘        └──────────────────┘
   Client-side              Server-side                  MCP Server
   (approval only)          (tool execution)             (tool provider)
```

Key difference from `FunctionTool`:
- **FunctionTool**: Agent decides to call → SDK executes local Python function → result sent back
- **McpTool**: Agent decides to call → Azure service calls remote MCP server → result sent back (client only handles approval)

## Quick Start

### 1. Create an MCP Tool

```python
from foundrykit import create_mcp_tool

mcp = create_mcp_tool(
    server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
    server_label="github-specs",
    allowed_tools=["search_code"],  # optional whitelist
    headers={"Authorization": "Bearer <token>"},  # optional auth
    approval_mode="never",  # "never" = auto-approve, "always" = require approval
)
```

### 2. Build a ToolSet

**Option A — MCP only:**

```python
from foundrykit import build_mcp_toolset

toolset = build_mcp_toolset(mcp)
```

**Option B — MCP + local functions (via ToolRegistry):**

```python
from foundrykit import ToolRegistry, create_mcp_tool

registry = ToolRegistry()

@registry.register
def my_local_tool(x: str) -> str:
    """A local tool function."""
    return f"Processed: {x}"

mcp = create_mcp_tool(
    server_url="https://example.com/mcp",
    server_label="external",
)
registry.add_mcp_tool(mcp)

toolset = registry.build_toolset()  # contains both local + MCP tools
```

### 3. Run with MCP

**Synchronous (create_and_process):**

```python
from foundrykit import AgentManager, McpRunHandler, get_foundry_client

client = get_foundry_client()
manager = AgentManager(client)
handler = McpRunHandler(mcp_tools=[mcp])

with manager.temporary_agent(
    name="my-agent",
    instructions="You are a helpful assistant.",
    toolset=toolset,
) as agent:
    result = manager.run_agent(
        agent.id,
        user_message="Search for Container Apps API.",
        run_handler=handler,
    )
    print(result)
```

**Streaming:**

```python
with manager.temporary_agent(
    name="my-agent",
    instructions="You are a helpful assistant.",
    toolset=toolset,
) as agent:
    for event in manager.run_agent_stream(
        agent.id,
        user_message="Search for Container Apps API.",
        mcp_tools=[mcp],
    ):
        if event.event_type == "text_delta":
            print(event.data, end="", flush=True)
        elif event.event_type == "mcp_approved":
            print(f"\n[MCP Approved: {event.metadata['tool_call_id']}]")
```

## MCP Tool Approval

By default, MCP tool calls require client-side approval before the Azure service executes them. The foundrykit library provides two ways to handle this:

### Auto-Approval (Default)

Set `approval_mode="never"` on the `McpTool` (this is the default in `create_mcp_tool`):

```python
mcp = create_mcp_tool(
    server_url="...",
    server_label="...",
    approval_mode="never",  # auto-approve all tool calls
)
```

### Manual Approval via RunHandler

For `create_and_process`, use `McpRunHandler`:

```python
handler = McpRunHandler(mcp_tools=[mcp], auto_approve=True)
result = manager.run_agent(agent.id, "message", run_handler=handler)
```

Set `auto_approve=False` to reject all MCP calls (useful for testing):

```python
handler = McpRunHandler(mcp_tools=[mcp], auto_approve=False)
```

### Streaming Approval

For streaming, pass `mcp_tools` to `run_agent_stream`. The `_StreamCollector` auto-approves MCP calls and emits `"mcp_approved"` events:

```python
for event in manager.run_agent_stream(agent.id, "msg", mcp_tools=[mcp]):
    if event.event_type == "mcp_approved":
        print(f"Approved: {event.metadata['tool_call_id']}")
```

## Multiple MCP Servers

Connect to multiple MCP servers simultaneously:

```python
github_mcp = create_mcp_tool(
    server_url="https://gitmcp.io/Azure/azure-rest-api-specs",
    server_label="github",
)

docs_mcp = create_mcp_tool(
    server_url="https://gitmcp.io/MicrosoftDocs/azure-ai-docs",
    server_label="azure-docs",
)

toolset = build_mcp_toolset(github_mcp, docs_mcp)
handler = McpRunHandler(mcp_tools=[github_mcp, docs_mcp])
```

## Custom Headers

Pass authentication headers to the MCP server:

```python
mcp = create_mcp_tool(
    server_url="https://api.example.com/mcp",
    server_label="private-api",
    headers={
        "Authorization": "Bearer <token>",
        "X-API-Key": "<key>",
    },
)
```

Headers are:
- Applied during tool creation
- Forwarded during approval (merged from all MCP tools in the handler)
- Manageable at runtime via `mcp.update_headers(key, value)`

## Tool Filtering

Restrict which tools the agent can call from an MCP server:

```python
mcp = create_mcp_tool(
    server_url="https://example.com/mcp",
    server_label="restricted",
    allowed_tools=["search_code", "get_file"],  # only these
)

# Dynamic management at runtime
mcp.allow_tool("list_repos")
mcp.disallow_tool("search_code")
```

## LoanFlow AI Integration

The loan-origination backend supports optional MCP integration. Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | _(empty)_ | MCP server URL; empty = disabled |
| `MCP_SERVER_LABEL` | `lending-mcp` | Human-readable label |
| `MCP_API_KEY` | _(empty)_ | Bearer token for MCP server auth |
| `MCP_ALLOWED_TOOLS` | _(empty)_ | Comma-separated tool whitelist |
| `MCP_APPROVAL_MODE` | `never` | `never` or `always` |

### Example: Connect to a Lending Regulations MCP

```bash
export MCP_SERVER_URL="https://lending-mcp.example.com/mcp"
export MCP_SERVER_LABEL="lending-regulations"
export MCP_API_KEY="your-api-key"
export MCP_ALLOWED_TOOLS="check_regulations,get_rate_sheet"
```

When `MCP_SERVER_URL` is set, the loan-origination agent will automatically:
1. Register the MCP tool alongside local function tools
2. Auto-approve MCP tool calls during streaming
3. Make remote tools available to the Foundry agent

When `MCP_SERVER_URL` is empty (default), the app operates in function-tools-only mode — no changes needed.

## API Reference

### `create_mcp_tool(**kwargs) → McpTool`

Factory function that creates a configured `McpTool`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_url` | `str` | _(required)_ | MCP server Streamable HTTP URL |
| `server_label` | `str` | _(required)_ | Human-readable server label |
| `allowed_tools` | `list[str] \| None` | `None` | Tool whitelist (empty = all) |
| `headers` | `dict[str, str] \| None` | `None` | Custom HTTP headers |
| `approval_mode` | `str` | `"never"` | `"never"` or `"always"` |

### `build_mcp_toolset(*mcp_tools, existing_toolset=None) → ToolSet`

Assembles a `ToolSet` from one or more `McpTool` instances.

### `McpRunHandler(mcp_tools=None, auto_approve=True)`

`RunHandler` subclass for auto-approving MCP tool calls during `create_and_process()`.

### `ToolRegistry.add_mcp_tool(mcp: McpTool)`

Registers a remote MCP tool in the registry alongside local function tools.

## Sample Scripts

Working examples are in `py/libs/foundrykit/samples/`:

| Script | Description |
|--------|-------------|
| `mcp_single_server.py` | Basic single MCP server setup |
| `mcp_multiple_servers.py` | Two MCP servers combined |
| `mcp_with_local_functions.py` | MCP + local function tools via ToolRegistry |
| `mcp_streaming.py` | Streaming with MCP tool approval |
| `mcp_advanced_config.py` | Custom headers, tool filtering, runtime management |

## Troubleshooting

### MCP tool calls not being approved

Ensure you're passing:
- `run_handler=McpRunHandler(mcp_tools=[mcp])` for `run_agent()`
- `mcp_tools=[mcp]` for `run_agent_stream()`

### MCP server returns 401/403

Check that headers are configured correctly:
```python
mcp = create_mcp_tool(
    server_url="...",
    server_label="...",
    headers={"Authorization": "Bearer <valid-token>"},
)
```

### SDK version mismatch

MCP support requires `azure-ai-agents >= 1.2.0b3`:
```bash
pip install "azure-ai-agents>=1.2.0b3" --pre
```

### Tests fail with ImportError for McpTool

Ensure `foundrykit` is installed from the workspace source:
```bash
cd py/libs/foundrykit
uv sync
```
