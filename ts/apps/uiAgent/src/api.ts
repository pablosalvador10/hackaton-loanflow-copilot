/** SSE streaming client for /api/v1/loan/stream (loan.py backend). */

export interface StreamRequest {
  conversation_id: string;
  message_id: string;
  message: string;
  history: { role: string; content: string }[];
  application_id: string | null;
  document_context: string | null;
}

export interface StreamCallbacks {
  onDelta: (text: string) => void;
  onDone: () => void;
  onError: (msg: string) => void;
}

export async function streamChat(
  request: StreamRequest,
  cb: StreamCallbacks,
): Promise<void> {
  try {
    const res = await fetch("/api/v1/loan/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) { cb.onError(`Server ${res.status}`); return; }
    const reader = res.body?.getReader();
    if (!reader) { cb.onError("No body"); return; }

    const decoder = new TextDecoder();
    let buf = "";
    let evt = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("event: ")) evt = line.slice(7).trim();
        else if (line.startsWith("data: ")) {
          try {
            const d = JSON.parse(line.slice(6));
            if (evt === "delta" && typeof d.text === "string") cb.onDelta(d.text);
            else if (evt === "done") cb.onDone();
            else if (evt === "error") cb.onError(d.message ?? "Unknown");
          } catch { /* skip */ }
          evt = "";
        }
      }
    }
  } catch (e) {
    cb.onError(e instanceof Error ? e.message : "Network error");
  }
}
