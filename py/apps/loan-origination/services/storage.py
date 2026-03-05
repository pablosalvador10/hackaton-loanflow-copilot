"""Storage interface with InMemory and Cosmos DB implementations.

Supports two modes via ``STORAGE_MODE``:

- ``inmemory`` — dict-backed storage for local development.
- ``cosmos``   — Azure Cosmos DB (Core/NoSQL) for production.

Four containers map to the domain models:

- ``applications``   — partitioned by ``/application_id``
- ``documents``      — partitioned by ``/application_id``
- ``conversations``  — partitioned by ``/conversation_id``
- ``audit_events``   — partitioned by ``/application_id``

Both implementations conform to the ``Storage`` protocol.
"""

from __future__ import annotations

from typing import Any, Protocol

import structlog
from azure.core import MatchConditions

from core.config import settings
from core.telemetry import get_tracer
from models.application import AuditEvent, Conversation, DocumentRecord, LoanApplication

logger = structlog.get_logger(__name__)
tracer = get_tracer("loan.storage")


# ── Protocol ─────────────────────────────────────────────────────


class Storage(Protocol):
    """Abstract storage interface for Loan Origination."""

    # Applications
    async def create_application(self, app: LoanApplication) -> LoanApplication: ...
    async def read_application(self, application_id: str) -> LoanApplication | None: ...
    async def update_application(self, app: LoanApplication) -> None: ...

    # Documents
    async def create_document(self, doc: DocumentRecord) -> DocumentRecord: ...
    async def read_document(self, document_id: str, application_id: str) -> DocumentRecord | None: ...
    async def list_documents_by_application(self, application_id: str) -> list[DocumentRecord]: ...
    async def update_document(self, doc: DocumentRecord) -> None: ...

    # Conversations
    async def read_conversation(self, conversation_id: str) -> Conversation | None: ...
    async def upsert_conversation(self, conversation: Conversation) -> None: ...

    # Audit events
    async def create_audit_event(self, event: AuditEvent) -> AuditEvent: ...
    async def list_audit_events(self, application_id: str) -> list[AuditEvent]: ...


# ── InMemory implementation ──────────────────────────────────────


class InMemoryStorage:
    """Dict-backed storage for local development."""

    def __init__(self) -> None:
        self._applications: dict[str, LoanApplication] = {}
        self._documents: dict[str, DocumentRecord] = {}
        self._conversations: dict[str, Conversation] = {}
        self._audit_events: list[AuditEvent] = []

    # -- Applications --------------------------------------------------

    async def create_application(self, app: LoanApplication) -> LoanApplication:
        with tracer.start_as_current_span("storage.create_application") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.application_id", app.application_id)
            self._applications[app.application_id] = app
            return app

    async def read_application(self, application_id: str) -> LoanApplication | None:
        with tracer.start_as_current_span("storage.read_application") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.application_id", application_id)
            result = self._applications.get(application_id)
            span.set_attribute("storage.found", result is not None)
            return result

    async def update_application(self, app: LoanApplication) -> None:
        with tracer.start_as_current_span("storage.update_application") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.application_id", app.application_id)
            self._applications[app.application_id] = app

    # -- Documents -----------------------------------------------------

    async def create_document(self, doc: DocumentRecord) -> DocumentRecord:
        with tracer.start_as_current_span("storage.create_document") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.document_id", doc.document_id)
            self._documents[doc.document_id] = doc
            return doc

    async def read_document(self, document_id: str, application_id: str) -> DocumentRecord | None:
        with tracer.start_as_current_span("storage.read_document") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.document_id", document_id)
            result = self._documents.get(document_id)
            span.set_attribute("storage.found", result is not None)
            return result

    async def list_documents_by_application(self, application_id: str) -> list[DocumentRecord]:
        with tracer.start_as_current_span("storage.list_documents_by_application") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.application_id", application_id)
            results = [
                d for d in self._documents.values() if d.application_id == application_id
            ]
            span.set_attribute("storage.count", len(results))
            return results

    async def update_document(self, doc: DocumentRecord) -> None:
        with tracer.start_as_current_span("storage.update_document") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.document_id", doc.document_id)
            self._documents[doc.document_id] = doc

    # -- Conversations -------------------------------------------------

    async def read_conversation(self, conversation_id: str) -> Conversation | None:
        with tracer.start_as_current_span("storage.read_conversation") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.conversation_id", conversation_id)
            result = self._conversations.get(conversation_id)
            span.set_attribute("storage.found", result is not None)
            return result

    async def upsert_conversation(self, conversation: Conversation) -> None:
        with tracer.start_as_current_span("storage.upsert_conversation") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.conversation_id", conversation.conversation_id)
            self._conversations[conversation.conversation_id] = conversation

    # -- Audit events --------------------------------------------------

    async def create_audit_event(self, event: AuditEvent) -> AuditEvent:
        with tracer.start_as_current_span("storage.create_audit_event") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.event_id", event.event_id)
            self._audit_events.append(event)
            return event

    async def list_audit_events(self, application_id: str) -> list[AuditEvent]:
        with tracer.start_as_current_span("storage.list_audit_events") as span:
            span.set_attribute("storage.backend", "inmemory")
            span.set_attribute("storage.application_id", application_id)
            results = [e for e in self._audit_events if e.application_id == application_id]
            span.set_attribute("storage.count", len(results))
            return results


# ── Cosmos DB implementation ─────────────────────────────────────


class CosmosStorage:
    """Azure Cosmos DB (Core/NoSQL) storage backend with Entra ID auth.

    Uses ``DefaultAzureCredential`` for RBAC-based authentication.
    Each container client is created once and reused (singleton pattern).
    """

    def __init__(self) -> None:
        from azure.cosmos.aio import CosmosClient
        from azure.identity.aio import DefaultAzureCredential

        self._credential = DefaultAzureCredential()
        self._client = CosmosClient(settings.cosmos_endpoint, credential=self._credential)
        self._db = self._client.get_database_client(settings.cosmos_database_name)
        self._applications = self._db.get_container_client(
            settings.cosmos_container_applications,
        )
        self._documents = self._db.get_container_client(
            settings.cosmos_container_documents,
        )
        self._conversations = self._db.get_container_client(
            settings.cosmos_container_conversations,
        )
        self._audit_events = self._db.get_container_client(
            settings.cosmos_container_audit_events,
        )
        logger.info(
            "cosmos_storage_initialised",
            endpoint=settings.cosmos_endpoint,
            database=settings.cosmos_database_name,
        )

    # -- Applications --------------------------------------------------

    async def create_application(self, app: LoanApplication) -> LoanApplication:
        with tracer.start_as_current_span("storage.create_application") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.application_id", app.application_id)
            doc = app.model_dump()
            doc["id"] = app.application_id
            await self._applications.create_item(doc)
            return app

    async def read_application(self, application_id: str) -> LoanApplication | None:
        with tracer.start_as_current_span("storage.read_application") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.application_id", application_id)
            try:
                doc = await self._applications.read_item(
                    item=application_id,
                    partition_key=application_id,
                )
                span.set_attribute("storage.found", True)
                return LoanApplication(**doc)
            except Exception:
                span.set_attribute("storage.found", False)
                return None

    async def update_application(self, app: LoanApplication) -> None:
        with tracer.start_as_current_span("storage.update_application") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.application_id", app.application_id)
            doc = app.model_dump()
            doc["id"] = app.application_id
            await self._applications.upsert_item(doc)

    # -- Documents -----------------------------------------------------

    async def create_document(self, doc_record: DocumentRecord) -> DocumentRecord:
        with tracer.start_as_current_span("storage.create_document") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.document_id", doc_record.document_id)
            doc = doc_record.model_dump()
            doc["id"] = doc_record.document_id
            await self._documents.create_item(doc)
            return doc_record

    async def read_document(
        self, document_id: str, application_id: str
    ) -> DocumentRecord | None:
        with tracer.start_as_current_span("storage.read_document") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.document_id", document_id)
            try:
                doc = await self._documents.read_item(
                    item=document_id,
                    partition_key=application_id,
                )
                span.set_attribute("storage.found", True)
                return DocumentRecord(**doc)
            except Exception:
                span.set_attribute("storage.found", False)
                return None

    async def list_documents_by_application(self, application_id: str) -> list[DocumentRecord]:
        with tracer.start_as_current_span("storage.list_documents_by_application") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.application_id", application_id)
            query = "SELECT * FROM c WHERE c.application_id = @app_id"
            parameters: list[dict[str, Any]] = [
                {"name": "@app_id", "value": application_id},
            ]
            items = self._documents.query_items(
                query=query,
                parameters=parameters,
                partition_key=application_id,
            )
            results = [DocumentRecord(**item) async for item in items]
            span.set_attribute("storage.count", len(results))
            return results

    async def update_document(self, doc_record: DocumentRecord) -> None:
        with tracer.start_as_current_span("storage.update_document") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.document_id", doc_record.document_id)
            doc = doc_record.model_dump()
            doc["id"] = doc_record.document_id
            await self._documents.upsert_item(doc)

    # -- Conversations -------------------------------------------------

    async def read_conversation(self, conversation_id: str) -> Conversation | None:
        with tracer.start_as_current_span("storage.read_conversation") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.conversation_id", conversation_id)
            try:
                doc = await self._conversations.read_item(
                    item=conversation_id,
                    partition_key=conversation_id,
                )
                span.set_attribute("storage.found", True)
                return Conversation(**doc)
            except Exception:
                span.set_attribute("storage.found", False)
                return None

    async def upsert_conversation(self, conversation: Conversation) -> None:
        with tracer.start_as_current_span("storage.upsert_conversation") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.conversation_id", conversation.conversation_id)
            doc = conversation.model_dump()
            doc["id"] = conversation.conversation_id
            etag = doc.pop("_etag", None)
            kwargs: dict[str, Any] = {"body": doc}
            if etag:
                kwargs["etag"] = etag
                kwargs["match_condition"] = MatchConditions.IfNotModified
            await self._conversations.upsert_item(**kwargs)

    # -- Audit events --------------------------------------------------

    async def create_audit_event(self, event: AuditEvent) -> AuditEvent:
        with tracer.start_as_current_span("storage.create_audit_event") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.event_id", event.event_id)
            doc = event.model_dump()
            doc["id"] = event.event_id
            await self._audit_events.create_item(doc)
            return event

    async def list_audit_events(self, application_id: str) -> list[AuditEvent]:
        with tracer.start_as_current_span("storage.list_audit_events") as span:
            span.set_attribute("storage.backend", "cosmos")
            span.set_attribute("storage.application_id", application_id)
            query = "SELECT * FROM c WHERE c.application_id = @app_id ORDER BY c.timestamp DESC"
            parameters: list[dict[str, Any]] = [
                {"name": "@app_id", "value": application_id},
            ]
            items = self._audit_events.query_items(
                query=query,
                parameters=parameters,
                partition_key=application_id,
            )
            results = [AuditEvent(**item) async for item in items]
            span.set_attribute("storage.count", len(results))
            return results


# ── Factory ──────────────────────────────────────────────────────

_storage_instance: Storage | None = None


def get_storage() -> Storage:
    """Return the storage singleton based on ``STORAGE_MODE``.

    First call creates either ``InMemoryStorage`` or ``CosmosStorage``
    depending on ``settings.storage_mode``. Subsequent calls return
    the cached instance.
    """
    global _storage_instance

    if _storage_instance is not None:
        return _storage_instance

    _storage_instance = CosmosStorage() if settings.storage_mode == "cosmos" else InMemoryStorage()

    logger.info("storage_initialised", mode=settings.storage_mode)
    return _storage_instance
