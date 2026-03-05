"""Audit event logging tool.

Logs workflow events to the audit trail for compliance and
traceability. Each event records who did what, when, and why.

This is a **synchronous** function (required by Foundry FunctionTool).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def log_audit_event(
    application_id: str,
    action_type: str,
    actor_type: str = "system",
    details: str = "{}",
) -> str:
    """Log an audit event for a loan application.

    Creates an audit record capturing a workflow transition.
    Used by the agent at each phase of the origination process
    to build a complete compliance trail.

    :param application_id: The loan application this event belongs to.
    :param action_type: What happened. One of:
        ``application_received``, ``doc_uploaded``, ``doc_validated``,
        ``doc_rejected``, ``extraction_complete``, ``application_assembled``,
        ``review_started``, ``approval_generated``, ``letter_sent``.
    :param actor_type: Who triggered this. One of: ``system``, ``user``, ``reviewer``.
    :param details: JSON string with additional event details.
    :return: JSON string confirming the logged event with its event_id.
    :raises RuntimeError: If event logging fails.
    """
    with tracer.start_as_current_span("tool.log_audit_event") as span:
        span.set_attribute("tool.name", "log_audit_event")
        span.set_attribute("tool.args.application_id", application_id)
        span.set_attribute("tool.args.action_type", action_type)
        span.set_attribute("tool.args.actor_type", actor_type)

        logger.info(
            "log_audit_event_start",
            application_id=application_id,
            action_type=action_type,
            actor_type=actor_type,
        )

        try:
            from models.application import _new_id

            # Parse details string to dict
            try:
                details_dict = json.loads(details) if details else {}
            except json.JSONDecodeError:
                details_dict = {"raw": details}

            event_id = _new_id()
            timestamp = datetime.now(UTC).isoformat()

            event_record = {
                "event_id": event_id,
                "application_id": application_id,
                "actor_type": actor_type,
                "action_type": action_type,
                "details": details_dict,
                "timestamp": timestamp,
                "logged": True,
            }

            result_json = json.dumps(event_record)
            span.set_attribute("tool.result.event_id", event_id)

            logger.info(
                "log_audit_event_complete",
                event_id=event_id,
                application_id=application_id,
                action_type=action_type,
            )

            return result_json

        except Exception as e:
            logger.exception(
                "log_audit_event_error",
                application_id=application_id,
                error=str(e),
            )
            span.set_attribute("tool.error", str(e))
            raise RuntimeError(
                f"Audit event logging failed: {e}"
            ) from e
