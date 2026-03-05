# Samples — foundrykit

Runnable examples showing how to use the `foundrykit` library to build and run Azure AI Foundry agents.

## Prerequisites

```bash
cd py
uv sync
```

Set these environment variables (or use a `.env` file):

| Variable | Required | Description |
|----------|----------|-------------|
| `FOUNDRY_PROJECT_ENDPOINT` | Yes | Azure AI Foundry project endpoint URL |
| `FOUNDRY_MODEL_DEPLOYMENT_NAME` | No | Model deployment name (default: `gpt-4-1`) |
| `FOUNDRY_CREDENTIAL_MODE` | No | `dev` (default) or `managed_identity` |

## Samples

| File | What it shows |
|------|---------------|
| `01_basic_agent.py` | Minimal agent — create, run, get response, cleanup |
| `02_agent_with_tools.py` | Register local Python functions as agent tools via `ToolRegistry` |
| `03_streaming_agent.py` | Stream agent responses token-by-token using `run_agent_stream()` |
| `04_mcp_single_server.py` | Connect to a remote MCP server and auto-approve tool calls |
| `05_mcp_streaming.py` | Stream responses while using MCP tools |
| `06_mcp_with_local_tools.py` | Combine remote MCP tools + local function tools in one agent |

## Running a sample

```bash
cd py
uv run python samples/01_basic_agent.py
```
