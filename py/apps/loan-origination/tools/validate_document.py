"""Document quality validation tool.

Checks an uploaded document image for quality issues such as blur,
glare, poor lighting, or insufficient readability. Uses Azure
Document Intelligence ``prebuilt-read`` model to assess OCR confidence.

This is a **synchronous** function (required by Foundry FunctionTool).
"""

from __future__ import annotations

import json

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)


def validate_document_quality(
    document_id: str,
    document_type: str,
    file_name: str,
    file_content_base64: str,
) -> str:
    """Validate the quality of an uploaded document image.

    Checks for common quality issues that would prevent accurate data
    extraction: blur, glare, shadows, partial visibility, low resolution.

    :param document_id: Unique identifier for the document record.
    :param document_type: Type of document (e.g. ``drivers_license``, ``w2``).
    :param file_name: Original file name.
    :param file_content_base64: Base64-encoded file content.
    :return: JSON string with validation result including quality score,
             pass/fail status, and any issues found.
    :raises RuntimeError: If the Document Intelligence API call fails.
    """
    with tracer.start_as_current_span("tool.validate_document_quality") as span:
        span.set_attribute("tool.name", "validate_document_quality")
        span.set_attribute("tool.args.document_id", document_id)
        span.set_attribute("tool.args.document_type", document_type)
        span.set_attribute("tool.args.file_name", file_name)

        logger.info(
            "validate_document_quality_start",
            document_id=document_id,
            document_type=document_type,
            file_name=file_name,
        )

        try:
            from core.config import settings

            if settings.document_intelligence_endpoint:
                # Use Azure Document Intelligence for real quality validation
                import base64

                from azure.ai.documentintelligence import DocumentIntelligenceClient
                from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
                from azure.core.credentials import AzureKeyCredential

                client = DocumentIntelligenceClient(
                    endpoint=settings.document_intelligence_endpoint,
                    credential=AzureKeyCredential(settings.document_intelligence_key),
                )

                file_bytes = base64.b64decode(file_content_base64)

                poller = client.begin_analyze_document(
                    "prebuilt-read",
                    AnalyzeDocumentRequest(bytes_source=file_bytes),
                )
                result = poller.result()

                # Assess quality from OCR confidence
                confidences = []
                if result.pages:
                    for page in result.pages:
                        if page.words:
                            for word in page.words:
                                if word.confidence is not None:
                                    confidences.append(word.confidence)

                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0.0
                )
                quality_issues = []

                if avg_confidence < 0.7:
                    quality_issues.append(
                        "Low OCR confidence — image may be blurry or poorly lit"
                    )
                if avg_confidence < 0.5:
                    quality_issues.append(
                        "Very low readability — document text is not clearly visible"
                    )
                if not confidences:
                    quality_issues.append(
                        "No text detected — ensure the document is fully visible"
                    )

                quality_passed = avg_confidence >= 0.7 and len(confidences) > 0

            else:
                # Stub mode: simulate quality check for local development
                avg_confidence = 0.95
                quality_issues = []
                quality_passed = True

            validation_result = {
                "document_id": document_id,
                "document_type": document_type,
                "file_name": file_name,
                "quality_passed": quality_passed,
                "confidence_score": round(avg_confidence, 4),
                "quality_issues": quality_issues,
                "guidance": [],
            }

            if not quality_passed:
                validation_result["guidance"] = [
                    "Ensure the full document is visible in the image",
                    "Use good, even lighting — avoid shadows and glare",
                    "Keep the camera steady to avoid blur",
                    "Place the document on a flat, contrasting surface",
                    "Avoid reflections on glossy or laminated documents",
                ]

            result_json = json.dumps(validation_result)
            span.set_attribute("tool.result.quality_passed", quality_passed)
            span.set_attribute("tool.result.confidence", avg_confidence)

            logger.info(
                "validate_document_quality_complete",
                document_id=document_id,
                quality_passed=quality_passed,
                confidence=avg_confidence,
                issues_count=len(quality_issues),
            )

            return result_json

        except Exception as e:
            logger.exception(
                "validate_document_quality_error",
                document_id=document_id,
                error=str(e),
            )
            span.set_attribute("tool.error", str(e))
            raise RuntimeError(
                f"Document quality validation failed: {e}"
            ) from e
