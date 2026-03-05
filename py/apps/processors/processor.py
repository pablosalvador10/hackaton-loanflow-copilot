"""Service Bus message processor — reads from handoff queues, writes to Cosmos DB.

Designed to run as a Container Apps Job (event-driven, KEDA Service Bus scaler).
Also runs standalone for local development/testing.

Usage (local):
    python -m backend.processors.processor

Environment variables:
    SERVICEBUS_NAMESPACE         Fully-qualified SB namespace (e.g. sb-xxx.servicebus.windows.net)
    COSMOS_ENDPOINT              Cosmos DB endpoint
    COSMOS_DATABASE_NAME         Cosmos DB database name (default: contoso-router)
    COSMOS_CONTAINER_SALES_LEADS Container name for sales leads (default: sales_leads)
    COSMOS_CONTAINER_CS_TICKETS  Container name for CS tickets (default: cs_tickets)
    MAX_WAIT_SECONDS             Max seconds to wait for new messages before exiting (default: 30)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus.aio import ServiceBusClient

# ── Configuration ────────────────────────────────────────────────

SERVICE_BUS_NAMESPACE = os.environ.get("SERVICEBUS_NAMESPACE", "")
COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE_NAME", "contoso-router")
SALES_CONTAINER = os.environ.get("COSMOS_CONTAINER_SALES_LEADS", "sales_leads")
CS_CONTAINER = os.environ.get("COSMOS_CONTAINER_CS_TICKETS", "cs_tickets")
SALES_QUEUE = os.environ.get("SALES_QUEUE_NAME", "sales-handoff")
CS_QUEUE = os.environ.get("CS_QUEUE_NAME", "customer-success-handoff")
MAX_WAIT_SECONDS = int(os.environ.get("MAX_WAIT_SECONDS", "30"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("handoff_processor")


# ── Document Builders ────────────────────────────────────────────


def build_sales_lead(event: dict) -> dict:
    """Build a SalesLead document from a handoff event."""
    conversation_id = event.get("conversation_id", "unknown")
    contact = event.get("contact", {})
    context = event.get("context", {})

    return {
        "id": str(uuid.uuid4()),
        "pk": conversation_id,
        "conversation_id": conversation_id,
        "type": "sales_lead",
        "status": "new",
        "contact_email": contact.get("email", ""),
        "contact_name": contact.get("name"),
        "reason": context.get("qualification_notes", ""),
        "opportunity_context": {
            "key_topics": context.get("key_topics", []),
            "company_signals": context.get("company_signals", ""),
            "qualification_notes": context.get("qualification_notes", ""),
        },
        "conversation_summary": event.get("conversation_summary", ""),
        "created_at_ms": int(time.time() * 1000),
        "trace_id": event.get("trace_id", ""),
    }


def build_cs_ticket(event: dict) -> dict:
    """Build a CSTicket document from a handoff event."""
    conversation_id = event.get("conversation_id", "unknown")
    contact = event.get("contact", {})
    context = event.get("context", {})

    return {
        "id": str(uuid.uuid4()),
        "pk": conversation_id,
        "conversation_id": conversation_id,
        "type": "cs_ticket",
        "status": "open",
        "contact_email": contact.get("email", ""),
        "contact_name": contact.get("name"),
        "reason": "; ".join(context.get("churn_signals", [])),
        "issue_details": {
            "churn_signals": context.get("churn_signals", []),
            "severity": context.get("severity", "medium"),
            "key_topics": context.get("key_topics", []),
        },
        "conversation_summary": event.get("conversation_summary", ""),
        "created_at_ms": int(time.time() * 1000),
        "trace_id": event.get("trace_id", ""),
    }


# ── Queue Processing ─────────────────────────────────────────────

QUEUE_CONFIG = {
    "sales-handoff": {
        "container": SALES_CONTAINER,
        "builder": build_sales_lead,
        "label": "SalesLead",
    },
    "customer-success-handoff": {
        "container": CS_CONTAINER,
        "builder": build_cs_ticket,
        "label": "CSTicket",
    },
}


async def drain_queue(
    sb_client: ServiceBusClient,
    cosmos_db,
    queue_name: str,
) -> int:
    """Receive and process all available messages from a single queue.

    Returns the number of messages processed.
    """
    config = QUEUE_CONFIG[queue_name]
    container = cosmos_db.get_container_client(config["container"])
    processed = 0

    async with sb_client.get_queue_receiver(
        queue_name, max_wait_time=MAX_WAIT_SECONDS
    ) as receiver:
        async for msg in receiver:
            try:
                body = json.loads(str(msg))
                document = config["builder"](body)
                await container.upsert_item(document)
                await receiver.complete_message(msg)
                processed += 1
                logger.info(
                    "%s created: conversation_id=%s, email=%s",
                    config["label"],
                    document.get("conversation_id"),
                    document.get("contact_email"),
                )
            except json.JSONDecodeError:
                logger.exception("Failed to parse message from %s — dead-lettering", queue_name)
                await receiver.dead_letter_message(msg, reason="InvalidJSON")
            except Exception:
                logger.exception("Failed to process message from %s — abandoning", queue_name)
                await receiver.abandon_message(msg)

    return processed


# ── Main ─────────────────────────────────────────────────────────


async def main() -> None:
    """Process messages from both handoff queues, then exit."""
    if not SERVICE_BUS_NAMESPACE:
        logger.error("SERVICEBUS_NAMESPACE is not set — exiting")
        sys.exit(1)
    if not COSMOS_ENDPOINT:
        logger.error("COSMOS_ENDPOINT is not set — exiting")
        sys.exit(1)

    logger.info(
        "Starting processor: sb=%s, cosmos=%s, db=%s",
        SERVICE_BUS_NAMESPACE,
        COSMOS_ENDPOINT,
        COSMOS_DATABASE,
    )

    credential = DefaultAzureCredential()
    sb_client = ServiceBusClient(
        fully_qualified_namespace=SERVICE_BUS_NAMESPACE,
        credential=credential,
    )
    cosmos_client = CosmosClient(url=COSMOS_ENDPOINT, credential=credential)
    cosmos_db = cosmos_client.get_database_client(COSMOS_DATABASE)

    try:
        total = 0
        for queue_name in QUEUE_CONFIG:
            count = await drain_queue(sb_client, cosmos_db, queue_name)
            total += count
            logger.info("Queue %s: processed %d messages", queue_name, count)

        logger.info("Processor complete — %d total messages processed", total)
    finally:
        await sb_client.close()
        await cosmos_client.close()
        await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
