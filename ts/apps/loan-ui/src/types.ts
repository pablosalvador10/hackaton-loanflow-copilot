/** Shared TypeScript types matching backend Pydantic models. */

/* ── Chat message ── */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

/* ── Document upload ── */

export interface UploadedDocument {
  documentId: string;
  fileName: string;
  documentType: string;
  base64Content: string;
}

/* ── Audit event ── */

export interface AuditEvent {
  event_id: string;
  application_id: string;
  timestamp: string;
  actor_type: string;
  action_type: string;
  details: Record<string, unknown>;
}

/* ── Document record ── */

export interface DocumentRecord {
  document_id: string;
  application_id: string;
  document_type: string;
  file_name: string;
  status: string;
  quality_issues: string[];
  extracted_fields: Record<string, unknown>;
  confidence_score: number | null;
}
