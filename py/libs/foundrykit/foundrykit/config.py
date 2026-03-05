"""Foundry project configuration via Pydantic Settings."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class FoundrySettings(BaseSettings):
    """Typed configuration for Azure AI Foundry projects.

    All values are loaded from environment variables (with ``.env`` fallback).

    :param foundry_project_endpoint: Azure AI Foundry project endpoint URL.
    :param foundry_model_deployment_name: Name of the model deployment to use.
    :param foundry_credential_mode: Credential strategy — ``dev`` uses
        ``DefaultAzureCredential``; ``managed_identity`` uses
        ``ManagedIdentityCredential``.
    :param azure_client_id: Managed identity client ID (only needed in
        ``managed_identity`` mode).
    """

    foundry_project_endpoint: str = ""
    foundry_model_deployment_name: str = "gpt-4-1"
    foundry_credential_mode: Literal["dev", "managed_identity"] = "dev"
    azure_client_id: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


foundry_settings = FoundrySettings()
