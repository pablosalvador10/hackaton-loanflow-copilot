"""Singleton wrapper around ``AgentsClient`` (Azure AI Agents SDK v2).

Handles environment-aware credential selection following Azure best practices:
- **dev** mode → ``DefaultAzureCredential`` (chains CLI / VS Code tokens).
- **managed_identity** mode → ``ManagedIdentityCredential`` (no fallback).

Usage::

    from foundrykit import get_foundry_client

    client = get_foundry_client()
    agents = client.agents_client
"""

from __future__ import annotations

import structlog
from azure.ai.agents import AgentsClient
from opentelemetry import trace

from foundrykit.config import FoundrySettings, foundry_settings

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer("foundrykit.client")


class FoundryClient:
    """Thread-safe singleton wrapper around :class:`AgentsClient`.

    Uses the standalone ``azure-ai-agents`` SDK (v2) directly rather than
    the ``azure-ai-projects`` proxy.

    :param settings: Foundry settings instance.  Defaults to the module-level
        ``foundry_settings`` singleton.
    """

    _instance: FoundryClient | None = None
    _agents_client: AgentsClient | None = None

    def __init__(self, settings: FoundrySettings | None = None) -> None:
        self._settings = settings or foundry_settings

    # ── Credential Factory ──────────────────────────────────────

    def _build_credential(self):
        """Create the appropriate credential based on the configured mode.

        :return: An ``azure.identity`` credential object.
        :raises ValueError: If ``foundry_credential_mode`` is not recognised.
        """
        mode = self._settings.foundry_credential_mode

        if mode == "dev":
            from azure.identity import DefaultAzureCredential

            logger.info("credential_mode", mode="dev", strategy="DefaultAzureCredential")
            return DefaultAzureCredential()

        if mode == "managed_identity":
            from azure.identity import ManagedIdentityCredential

            client_id = self._settings.azure_client_id or None
            logger.info(
                "credential_mode",
                mode="managed_identity",
                client_id=client_id or "system-assigned",
            )
            return ManagedIdentityCredential(client_id=client_id)

        raise ValueError(f"Unknown foundry_credential_mode: {mode!r}")

    # ── Agents Client ───────────────────────────────────────────

    @property
    def agents_client(self) -> AgentsClient:
        """Lazily initialised ``AgentsClient`` singleton (v2 SDK).

        :return: Configured agents client.
        :raises RuntimeError: If ``foundry_project_endpoint`` is not set.
        """
        if self._agents_client is None:
            endpoint = self._settings.foundry_project_endpoint
            if not endpoint:
                raise RuntimeError(
                    "FOUNDRY_PROJECT_ENDPOINT is not set.  "
                    "Set it in your .env file or environment variables."
                )

            with tracer.start_as_current_span("foundrykit.create_agents_client") as span:
                span.set_attribute("foundry.endpoint", endpoint)
                credential = self._build_credential()
                self._agents_client = AgentsClient(
                    endpoint=endpoint,
                    credential=credential,
                )
                logger.info(
                    "agents_client_created",
                    endpoint=endpoint,
                )
        return self._agents_client

    @property
    def model_deployment(self) -> str:
        """Return the configured model deployment name.

        :return: Deployment name string.
        """
        return self._settings.foundry_model_deployment_name


# ── Module-level singleton ──────────────────────────────────────

_client: FoundryClient | None = None


def get_foundry_client(settings: FoundrySettings | None = None) -> FoundryClient:
    """Return the global ``FoundryClient`` singleton, creating it on first call.

    :param settings: Optional settings override (used mainly for testing).
    :return: Shared ``FoundryClient`` instance.
    """
    global _client
    if _client is None:
        _client = FoundryClient(settings=settings)
    return _client
