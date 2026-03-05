/* eslint-disable react-refresh/only-export-components */
/**
 * Conversation state management hook with persistence.
 *
 * Storage strategy:
 * - sessionStorage only (no auth — survives refresh, gone on tab close)
 *
 * Exposed as a React context so the header, chat page, and
 * upload components all share the same state.
 */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  useEffect,
  type ReactNode,
} from "react";
import { streamConversationMessage } from "@/lib/api";
import type { ChatMessage, ToolCallState, UploadedDocument } from "@/types";
import type { ToastData } from "@/components/chat/toast";

/* ── Types ── */

export interface StoredConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

interface ConversationState {
  messages: ChatMessage[];
  isLoading: boolean;
  toolCall: ToolCallState;
  conversationId: string;
  applicationId: string | null;
  conversations: StoredConversation[];
  toasts: ToastData[];
  /** Pending document to attach to next message. */
  pendingDocument: UploadedDocument | null;
  dismissToast: (id: string) => void;
  loadConversation: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  clearConversation: () => void;
  setPendingDocument: (doc: UploadedDocument | null) => void;
  setApplicationId: (id: string) => void;
}

/* ── Storage keys ── */

const SS_CONVS = "loan_convs";
const SS_ACTIVE = "loan_active";

/* ── Storage helpers ── */

function deriveTitle(msgs: ChatMessage[]): string {
  const first = msgs.find((m) => m.role === "user");
  if (!first) return "New application";
  const t = first.content.trim();
  return t.length > 50 ? t.slice(0, 47) + "…" : t;
}

function readConvs(): StoredConversation[] {
  try {
    const raw = sessionStorage.getItem(SS_CONVS);
    return raw
      ? (JSON.parse(raw) as StoredConversation[]).sort(
          (a, b) => b.updatedAt - a.updatedAt
        )
      : [];
  } catch {
    return [];
  }
}

function writeConvs(convs: StoredConversation[]) {
  sessionStorage.setItem(SS_CONVS, JSON.stringify(convs));
}

function readActiveId(): string | null {
  try {
    return sessionStorage.getItem(SS_ACTIVE);
  } catch {
    return null;
  }
}

function writeActiveId(id: string) {
  sessionStorage.setItem(SS_ACTIVE, id);
}

function upsert(
  list: StoredConversation[],
  convId: string,
  msgs: ChatMessage[]
): StoredConversation[] {
  if (msgs.length === 0) return list;

  const now = Date.now();
  const idx = list.findIndex((c) => c.id === convId);
  let updated: StoredConversation[];

  if (idx >= 0) {
    updated = list.map((c) =>
      c.id === convId
        ? {
            ...c,
            messages: msgs,
            updatedAt: now,
            title: deriveTitle(msgs),
          }
        : c
    );
  } else {
    updated = [
      {
        id: convId,
        title: deriveTitle(msgs),
        messages: msgs,
        createdAt: now,
        updatedAt: now,
      },
      ...list,
    ];
  }

  updated.sort((a, b) => b.updatedAt - a.updatedAt);
  writeConvs(updated);
  return updated;
}

/* ── Context ── */

const ConversationContext = createContext<ConversationState | null>(null);

/* ── Provider ── */

export function ConversationProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<StoredConversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [toolCall, setToolCall] = useState<ToolCallState>({ active: false, toolNames: [] });
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const [pendingDocument, setPendingDocument] = useState<UploadedDocument | null>(null);
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const convIdRef = useRef<string>(crypto.randomUUID());
  const isLoadingRef = useRef(false);

  const convsRef = useRef(conversations);
  convsRef.current = conversations;
  const msgsRef = useRef(messages);
  msgsRef.current = messages;
  isLoadingRef.current = isLoading;

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  /* ── Initial load from sessionStorage ── */

  useEffect(() => {
    const loaded = readConvs();
    if (loaded.length > 0) {
      setConversations(loaded);
      const activeId = readActiveId();
      const active = activeId
        ? loaded.find((c) => c.id === activeId)
        : loaded[0];
      if (active) {
        convIdRef.current = active.id;
        setMessages(active.messages);
      }
    }
  }, []);

  /* ── Auto-save on every message change ── */

  useEffect(() => {
    if (messages.length === 0) return;
    const updated = upsert(
      convsRef.current,
      convIdRef.current,
      messages
    );
    setConversations(updated);
    writeActiveId(convIdRef.current);
  }, [messages]);

  /* ── Actions ── */

  const loadConversation = useCallback((id: string) => {
    if (msgsRef.current.length > 0) {
      const updated = upsert(
        convsRef.current,
        convIdRef.current,
        msgsRef.current
      );
      setConversations(updated);
    }
    const target = convsRef.current.find((c) => c.id === id);
    if (target) {
      convIdRef.current = target.id;
      setMessages(target.messages);
      writeActiveId(target.id);
    }
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (isLoadingRef.current) return;

    const messageId = crypto.randomUUID();
    const userMsg: ChatMessage = {
      id: messageId,
      role: "user",
      content,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const botMsgId = crypto.randomUUID();
    const botMsg: ChatMessage = {
      id: botMsgId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, botMsg]);

    const history = msgsRef.current
      .filter((m) => m.id !== messageId && m.id !== botMsgId)
      .map((m) => ({ role: m.role, content: m.content }));

    // Attach document context if pending
    const docContext = pendingDocument?.base64Content ?? null;
    const docMeta = pendingDocument
      ? JSON.stringify({
          document_id: pendingDocument.documentId,
          document_type: pendingDocument.documentType,
          file_name: pendingDocument.fileName,
          file_content_base64: pendingDocument.base64Content,
        })
      : null;

    // Clear pending document after attaching
    if (pendingDocument) {
      setPendingDocument(null);
    }

    streamConversationMessage(
      {
        conversation_id: convIdRef.current,
        message_id: messageId,
        message: content,
        history,
        application_id: applicationId,
        document_context: docMeta ?? docContext,
      },
      {
        onDelta: (text: string) => {
          // First token: clear the tool call indicator
          setToolCall({ active: false, toolNames: [] });
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, content: m.content + text } : m
            )
          );
        },
        onToolStart: (toolNames: string[]) => {
          setToolCall({ active: true, toolNames });
        },
        onToolDone: () => {
          setToolCall({ active: false, toolNames: [] });
        },
        onDone: (_data: Record<string, unknown>) => {
          setToolCall({ active: false, toolNames: [] });
          setIsLoading(false);
        },
        onError: (message: string) => {
          setToolCall({ active: false, toolNames: [] });
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? { ...m, content: m.content || `Sorry, something went wrong: ${message}` }
                : m
            )
          );
        },
      }
    );
  }, [pendingDocument, applicationId]);

  const clearConversation = useCallback(() => {
    if (msgsRef.current.length > 0) {
      const updated = upsert(
        convsRef.current,
        convIdRef.current,
        msgsRef.current
      );
      setConversations(updated);
    }
    setMessages([]);
    setIsLoading(false);
    setPendingDocument(null);
    setApplicationId(null);
    convIdRef.current = crypto.randomUUID();
    writeActiveId(convIdRef.current);
  }, []);

  return (
    <ConversationContext.Provider
      value={{
        messages,
        isLoading,
        toolCall,
        conversationId: convIdRef.current,
        applicationId,
        conversations,
        toasts,
        pendingDocument,
        dismissToast,
        loadConversation,
        sendMessage,
        clearConversation,
        setPendingDocument,
        setApplicationId,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

export function useConversation(): ConversationState {
  const ctx = useContext(ConversationContext);
  if (!ctx) {
    throw new Error(
      "useConversation must be used within a ConversationProvider"
    );
  }
  return ctx;
}
