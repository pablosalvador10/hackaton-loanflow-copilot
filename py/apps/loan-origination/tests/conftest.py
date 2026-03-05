"""Shared pytest fixtures for Loan Origination tests."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

from pydantic_settings import BaseSettings

# Ensure the app root is importable (tools/, api/, core/ etc.)
_app_root = Path(__file__).resolve().parents[1]
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))


def _ensure_foundrykit_importable() -> None:
    """Inject mock ``foundrykit`` modules if the package is not installed.

    Creates fake submodules (``foundrykit.config``, ``foundrykit.client``,
    ``foundrykit.agent``, ``foundrykit.tools``) with stub classes so that
    the Loan Origination app can be imported in tests without Azure credentials.
    """
    if "foundrykit" in sys.modules:
        return

    try:
        import foundrykit  # noqa: F401

        return
    except ImportError:
        pass

    # ── Build a mock FoundrySettings class that can be subclassed ──
    class _MockFoundrySettings(BaseSettings):
        """Stub replacement for ``foundrykit.config.FoundrySettings``."""

        foundry_project_endpoint: str = ""
        foundry_model_deployment_name: str = "gpt-4-1-nano"
        foundry_credential_mode: str = "dev"
        azure_client_id: str = ""

        model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── foundrykit.config ──
    config_mod = ModuleType("foundrykit.config")
    config_mod.FoundrySettings = _MockFoundrySettings  # type: ignore[attr-defined]
    config_mod.foundry_settings = _MockFoundrySettings()  # type: ignore[attr-defined]
    sys.modules["foundrykit.config"] = config_mod

    # ── foundrykit.client ──
    client_mod = ModuleType("foundrykit.client")
    client_mod.FoundryClient = MagicMock  # type: ignore[attr-defined]
    client_mod.get_foundry_client = MagicMock()  # type: ignore[attr-defined]
    sys.modules["foundrykit.client"] = client_mod

    # ── foundrykit.agent ──
    agent_mod = ModuleType("foundrykit.agent")
    agent_mod.AgentManager = MagicMock  # type: ignore[attr-defined]
    sys.modules["foundrykit.agent"] = agent_mod

    # ── foundrykit.tools ──
    tools_mod = ModuleType("foundrykit.tools")
    tools_mod.ToolRegistry = MagicMock  # type: ignore[attr-defined]
    sys.modules["foundrykit.tools"] = tools_mod

    # ── foundrykit.mcp ──
    mcp_mod = ModuleType("foundrykit.mcp")
    mcp_mod.create_mcp_tool = MagicMock(return_value=None)  # type: ignore[attr-defined]
    mcp_mod.McpRunHandler = MagicMock  # type: ignore[attr-defined]
    mcp_mod.build_mcp_toolset = MagicMock  # type: ignore[attr-defined]
    sys.modules["foundrykit.mcp"] = mcp_mod

    # ── foundrykit (top-level package) ──
    pkg_mod = ModuleType("foundrykit")
    pkg_mod.AgentManager = MagicMock  # type: ignore[attr-defined]
    pkg_mod.FoundryClient = MagicMock  # type: ignore[attr-defined]
    pkg_mod.FoundrySettings = _MockFoundrySettings  # type: ignore[attr-defined]
    pkg_mod.ToolRegistry = MagicMock  # type: ignore[attr-defined]
    pkg_mod.McpRunHandler = MagicMock  # type: ignore[attr-defined]
    pkg_mod.create_mcp_tool = mcp_mod.create_mcp_tool  # type: ignore[attr-defined]
    pkg_mod.build_mcp_toolset = mcp_mod.build_mcp_toolset  # type: ignore[attr-defined]
    pkg_mod.foundry_settings = config_mod.foundry_settings  # type: ignore[attr-defined]
    pkg_mod.get_foundry_client = client_mod.get_foundry_client  # type: ignore[attr-defined]
    pkg_mod.config = config_mod  # type: ignore[attr-defined]
    pkg_mod.client = client_mod  # type: ignore[attr-defined]
    pkg_mod.agent = agent_mod  # type: ignore[attr-defined]
    pkg_mod.tools = tools_mod  # type: ignore[attr-defined]
    pkg_mod.mcp = mcp_mod  # type: ignore[attr-defined]
    sys.modules["foundrykit"] = pkg_mod


_ensure_foundrykit_importable()
