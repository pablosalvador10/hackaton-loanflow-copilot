"""Application settings for the Loan Origination service."""

from __future__ import annotations

from typing import Literal

from foundrykit.config import FoundrySettings


class LoanOriginationSettings(FoundrySettings):
    """Configuration for the Loan Origination agent service.

    Extends ``FoundrySettings`` with loan-origination-specific settings.

    :param storage_mode: Storage backend (``inmemory`` for dev, ``cosmos`` for Azure).
    :param otel_exporter: OpenTelemetry exporter mode.
    :param document_intelligence_endpoint: Azure Document Intelligence endpoint URL.
    :param document_intelligence_key: Azure Document Intelligence API key (dev only).
    :param api_host: Host to bind the FastAPI server.
    :param api_port: Port to bind the FastAPI server.
    :param log_level: Root log level.
    :param cors_origins: Comma-separated allowed CORS origins.
    """

    # Azure Document Intelligence
    document_intelligence_endpoint: str = ""
    document_intelligence_key: str = ""

    # MCP server (optional — enables remote tool servers)
    mcp_server_url: str = ""
    mcp_server_label: str = "lending-mcp"
    mcp_api_key: str = ""
    mcp_allowed_tools: str = ""
    mcp_approval_mode: str = "never"

    # Runtime modes
    storage_mode: Literal["inmemory", "cosmos"] = "inmemory"
    otel_exporter: Literal["console", "aitoolkit", "azure"] = "console"

    # Cosmos DB
    cosmos_endpoint: str = ""
    cosmos_database_name: str = "loan-origination"
    cosmos_container_applications: str = "applications"
    cosmos_container_documents: str = "documents"
    cosmos_container_conversations: str = "conversations"
    cosmos_container_audit_events: str = "audit_events"

    # Observability
    applicationinsights_connection_string: str = ""

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    log_level: str = "INFO"
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
        "http://localhost:5176,http://localhost:5177,http://localhost:5178"
    )

    model_config = {  # noqa: RUF012
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = LoanOriginationSettings()
