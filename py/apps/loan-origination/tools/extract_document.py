"""Document field extraction tool.

Classifies uploaded documents and extracts structured fields using
Azure Document Intelligence pre-built models:

- ``prebuilt-idDocument``  — driver's licenses, passports
- ``prebuilt-tax.us.w2``   — W-2 tax forms
- ``prebuilt-document``    — bank statements, pay stubs, other docs

This is a **synchronous** function (required by Foundry FunctionTool).
"""

from __future__ import annotations

import json

import structlog
from opentelemetry import trace

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

# Map document types to Document Intelligence model IDs
_MODEL_MAP = {
    "drivers_license": "prebuilt-idDocument",
    "w2": "prebuilt-tax.us.w2",
    "bank_statement": "prebuilt-document",
    "pay_stub": "prebuilt-document",
    "investment_statement": "prebuilt-document",
    "other": "prebuilt-document",
}


def extract_document_fields(
    document_id: str,
    document_type: str,
    file_name: str,
    file_content_base64: str,
) -> str:
    """Extract structured fields from an uploaded document.

    Uses the appropriate Azure Document Intelligence pre-built model
    based on the document type. Returns extracted key-value pairs with
    confidence scores.

    :param document_id: Unique identifier for the document record.
    :param document_type: Type of document (e.g. ``drivers_license``, ``w2``).
    :param file_name: Original file name.
    :param file_content_base64: Base64-encoded file content.
    :return: JSON string with extracted fields, confidence scores, and
             the document classification.
    :raises RuntimeError: If extraction fails.
    """
    with tracer.start_as_current_span("tool.extract_document_fields") as span:
        span.set_attribute("tool.name", "extract_document_fields")
        span.set_attribute("tool.args.document_id", document_id)
        span.set_attribute("tool.args.document_type", document_type)

        logger.info(
            "extract_document_fields_start",
            document_id=document_id,
            document_type=document_type,
            file_name=file_name,
        )

        try:
            from core.config import settings

            model_id = _MODEL_MAP.get(document_type, "prebuilt-document")

            if settings.document_intelligence_endpoint:
                # Use Azure Document Intelligence for real extraction
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
                    model_id,
                    AnalyzeDocumentRequest(bytes_source=file_bytes),
                )
                result = poller.result()

                # Extract fields from the result
                extracted = {}
                overall_confidence = 0.0
                field_count = 0

                if result.documents:
                    for doc in result.documents:
                        if doc.fields:
                            for field_name, field_value in doc.fields.items():
                                extracted[field_name] = {
                                    "value": str(field_value.content) if field_value.content else "",
                                    "confidence": field_value.confidence or 0.0,
                                }
                                if field_value.confidence:
                                    overall_confidence += field_value.confidence
                                    field_count += 1

                if field_count > 0:
                    overall_confidence /= field_count

            else:
                # Stub mode: return realistic mock data for local development
                extracted, overall_confidence = _get_stub_extraction(document_type)

            extraction_result = {
                "document_id": document_id,
                "document_type": document_type,
                "model_used": model_id,
                "file_name": file_name,
                "extraction_status": "completed",
                "overall_confidence": round(overall_confidence, 4),
                "extracted_fields": extracted,
                "field_count": len(extracted),
            }

            result_json = json.dumps(extraction_result)
            span.set_attribute("tool.result.field_count", len(extracted))
            span.set_attribute("tool.result.confidence", overall_confidence)

            logger.info(
                "extract_document_fields_complete",
                document_id=document_id,
                field_count=len(extracted),
                confidence=overall_confidence,
            )

            return result_json

        except Exception as e:
            logger.exception(
                "extract_document_fields_error",
                document_id=document_id,
                error=str(e),
            )
            span.set_attribute("tool.error", str(e))
            raise RuntimeError(
                f"Document field extraction failed: {e}"
            ) from e


def _get_stub_extraction(document_type: str) -> tuple[dict, float]:
    """Return realistic mock extracted fields for local development.

    :param document_type: The type of document being extracted.
    :return: Tuple of (extracted_fields_dict, overall_confidence).
    """
    if document_type == "drivers_license":
        return {
            "FirstName": {"value": "John", "confidence": 0.99},
            "LastName": {"value": "Doe", "confidence": 0.99},
            "Address": {"value": "123 Main St, Houston, TX 77001", "confidence": 0.97},
            "DateOfBirth": {"value": "1985-06-15", "confidence": 0.98},
            "DocumentNumber": {"value": "DL12345678", "confidence": 0.99},
            "ExpirationDate": {"value": "2028-06-15", "confidence": 0.98},
            "State": {"value": "Texas", "confidence": 0.99},
        }, 0.9857

    elif document_type == "w2":
        return {
            "EmployeeName": {"value": "John Doe", "confidence": 0.98},
            "EmployerName": {"value": "Acme Corporation", "confidence": 0.97},
            "WagesTipsOtherCompensation": {"value": "75320.70", "confidence": 0.99},
            "FederalIncomeTaxWithheld": {"value": "15064.14", "confidence": 0.98},
            "SocialSecurityWages": {"value": "75320.70", "confidence": 0.99},
            "EmployeeSSN": {"value": "***-**-1234", "confidence": 0.97},
            "EmployerEIN": {"value": "12-3456789", "confidence": 0.98},
            "TaxYear": {"value": "2025", "confidence": 0.99},
        }, 0.9813

    elif document_type == "bank_statement":
        return {
            "AccountHolderName": {"value": "John Doe", "confidence": 0.97},
            "BankName": {"value": "First National Bank", "confidence": 0.98},
            "AccountNumber": {"value": "****5678", "confidence": 0.96},
            "StatementPeriod": {"value": "01/2026 - 02/2026", "confidence": 0.95},
            "EndingBalance": {"value": "59235.71", "confidence": 0.98},
            "AverageBalance": {"value": "55420.30", "confidence": 0.97},
        }, 0.9683

    elif document_type == "investment_statement":
        return {
            "AccountHolderName": {"value": "John Doe", "confidence": 0.97},
            "BrokerageName": {"value": "Vanguard", "confidence": 0.98},
            "AccountNumber": {"value": "****9012", "confidence": 0.96},
            "TotalPortfolioValue": {"value": "123084.85", "confidence": 0.98},
            "StatementDate": {"value": "2026-02-28", "confidence": 0.97},
        }, 0.9720

    elif document_type == "pay_stub":
        return {
            "EmployeeName": {"value": "John Doe", "confidence": 0.98},
            "EmployerName": {"value": "Acme Corporation", "confidence": 0.97},
            "GrossPay": {"value": "6276.73", "confidence": 0.98},
            "NetPay": {"value": "4822.50", "confidence": 0.98},
            "PayPeriod": {"value": "02/01/2026 - 02/28/2026", "confidence": 0.97},
            "YTDGross": {"value": "12553.45", "confidence": 0.97},
        }, 0.9750

    else:
        return {
            "DocumentContent": {"value": "Document processed", "confidence": 0.90},
        }, 0.9000
