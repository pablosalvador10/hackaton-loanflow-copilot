/** Shared TypeScript types matching backend Pydantic models. */

/* ── Chat message ── */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  traceDetails?: TraceDetails;
}

/* ── Inline trace viewer ── */

export interface TraceSpan {
  name: string;
  duration_ms: number;
  attributes: Record<string, string | number | boolean>;
  children: TraceSpan[];
}

export interface TraceDetails {
  trace_id: string;
  spans: TraceSpan;
}
