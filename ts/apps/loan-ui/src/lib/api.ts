import type { AuditEvent, DocumentRecord } from "@/types";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL || "http://localhost:8002";

/* ── Types ── */

interface ChatMessagePayload {
  role: string;
  content: string;
}

interface StreamRequestBody {
  conversation_id: string;
  message_id: string;
  message: string;
  history: ChatMessagePayload[];
  application_id?: string | null;
  document_context?: string | null;
}

interface StreamCallbacks {
  onDelta: (text: string) => void;
  onDone: (data: Record<string, unknown>) => void;
  onError: (message: string) => void;
  /** Called when the agent starts invoking one or more tools. */
  onToolStart?: (toolNames: string[]) => void;
  /** Called when tool execution completes. */
  onToolDone?: () => void;
  /** Called when the backend indicates a rich card should be shown. */
  onCard?: (cardType: string, data: Record<string, unknown>) => void;
}

interface UploadResponse {
  document_id: string;
  file_name: string;
  message: string;
}

/* ── SSE streaming loan conversation ── */

/**
 * Stream a loan origination conversation from the backend via SSE.
 *
 * @returns An `AbortController` that the caller can use to cancel the stream.
 */
export function streamConversationMessage(
  body: StreamRequestBody,
  callbacks: StreamCallbacks
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/v1/loan/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: controller.signal,
        }
      );

      if (!response.ok) {
        callbacks.onError(
          `API error: ${response.status} ${response.statusText}`
        );
        callbacks.onDone({});
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError("No response body");
        callbacks.onDone({});
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const lines = part.split("\n");
          let eventType = "";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              data = line.slice(6);
            }
          }

          if (!eventType || !data) continue;

          try {
            const parsed = JSON.parse(data) as Record<string, unknown>;

            switch (eventType) {
              case "delta":
                if (typeof parsed.text === "string") {
                  callbacks.onDelta(parsed.text);
                }
                break;
              case "tool_start": {
                const names = Array.isArray(parsed.tool_names)
                  ? (parsed.tool_names as string[])
                  : [];
                callbacks.onToolStart?.(names);
                break;
              }
              case "tool_done":
                callbacks.onToolDone?.();
                break;
              case "card":
                if (typeof parsed.type === "string") {
                  callbacks.onCard?.(
                    parsed.type,
                    (parsed.data as Record<string, unknown>) ?? {},
                  );
                }
                break;
              case "done":
                callbacks.onDone(parsed);
                return;
              case "error":
                callbacks.onError(
                  typeof parsed.message === "string"
                    ? parsed.message
                    : "Unknown error"
                );
                break;
            }
          } catch {
            // Ignore malformed JSON in SSE data
          }
        }
      }

      // If stream ended without a done event, fire done anyway
      callbacks.onDone({});
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError(
          err instanceof Error ? err.message : "Stream failed"
        );
        callbacks.onDone({});
      }
    }
  })();

  return controller;
}

/* ── Document upload ── */

export async function uploadDocument(
  file: File,
  documentType: string,
  applicationId?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);
  if (applicationId) {
    formData.append("application_id", applicationId);
  }

  const response = await fetch(`${BACKEND_URL}/api/v1/loan/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(
      detail?.detail ?? `Upload failed: ${response.status} ${response.statusText}`
    );
  }

  return (await response.json()) as UploadResponse;
}

/* ── Application details ── */

export async function getApplication(
  applicationId: string
): Promise<Record<string, unknown>> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/loan/${applicationId}`
  );
  if (!response.ok) throw new Error(`Application not found: ${applicationId}`);
  return (await response.json()) as Record<string, unknown>;
}

/* ── Audit trail ── */

export async function getAuditTrail(
  applicationId: string
): Promise<AuditEvent[]> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/loan/${applicationId}/audit`
  );
  if (!response.ok) return [];
  return (await response.json()) as AuditEvent[];
}

/* ── Documents list ── */

export async function getDocuments(
  applicationId: string
): Promise<DocumentRecord[]> {
  const response = await fetch(
    `${BACKEND_URL}/api/v1/loan/${applicationId}/documents`
  );
  if (!response.ok) return [];
  return (await response.json()) as DocumentRecord[];
}

/* ── Health check ── */

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/healthz`);
    return res.ok;
  } catch {
    return false;
  }
}
