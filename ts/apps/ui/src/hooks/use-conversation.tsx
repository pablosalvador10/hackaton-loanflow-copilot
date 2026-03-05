/* eslint-disable react-refresh/only-export-components */
/**
 * Conversation state management hook with persistence.
 *
 * Storage strategy:
 * - sessionStorage only (no auth — survives refresh, gone on tab close)
 *
 * Exposed as a React context so the header, chat page, and
 * conversation-history components all share the same state.
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
import type { ChatMessage } from "@/types";
import type { ToastData } from "@/components/chat/toast";

/* ── Types ── */

/** A persisted conversation with metadata. */
export interface StoredConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

/* ── Public interface ── */

interface ConversationState {
  messages: ChatMessage[];
  isLoading: boolean;
  conversationId: string;
  /** All saved conversations for the current session (most recent first). */
  conversations: StoredConversation[];
  /** Active toast notifications. */
  toasts: ToastData[];
  /** Dismiss a toast by ID. */
  dismissToast: (id: string) => void;
  /** Switch to a previously saved conversation. */
  loadConversation: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  /** Save current conversation (if non-empty) and start a new one. */
  clearConversation: () => void;
}

/* ── Storage keys ── */

const SS_CONVS = "vin_convs";
const SS_ACTIVE = "vin_active";

/* ── Storage helpers ── */

function deriveTitle(msgs: ChatMessage[]): string {
  const first = msgs.find((m) => m.role === "user");
  if (!first) return "New lookup";
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

/**
 * Insert-or-update a conversation in a list and persist it.
 * Returns the updated list sorted most-recent first.
 */
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
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const convIdRef = useRef<string>(crypto.randomUUID());
  const isLoadingRef = useRef(false);

  // Live refs to avoid stale closures across async gaps
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

  /** Switch to a previously saved conversation. */
  const loadConversation = useCallback((id: string) => {
    // Save current before switching
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

  /**
   * Send a user message and stream the VIN insight report from the backend.
   */
  const sendMessage = useCallback(async (content: string) => {
    if (isLoadingRef.current) {
      return;
    }

    const messageId = crypto.randomUUID();
    const userMsg: ChatMessage = {
      id: messageId,
      role: "user",
      content,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Create a placeholder bot message for streaming into
    const botMsgId = crypto.randomUUID();
    const botMsg: ChatMessage = {
      id: botMsgId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, botMsg]);

    // Build the history from current messages (excluding the just-added ones)
    const history = msgsRef.current
      .filter((m) => m.id !== messageId && m.id !== botMsgId)
      .map((m) => ({ role: m.role, content: m.content }));

    streamConversationMessage(
      {
        conversation_id: convIdRef.current,
        message_id: messageId,
        message: content,
        history,
      },
      {
        onDelta: (text: string) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, content: m.content + text } : m
            )
          );
        },
        onDone: () => {
          setIsLoading(false);
        },
        onError: (message: string) => {
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
  }, []);

  /** Save current conversation (if any) and start a fresh one. */
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
    convIdRef.current = crypto.randomUUID();
    writeActiveId(convIdRef.current);
  }, []);

  return (
    <ConversationContext.Provider
      value={{
        messages,
        isLoading,
        conversationId: convIdRef.current,
        conversations,
        toasts,
        dismissToast,
        loadConversation,
        sendMessage,
        clearConversation,
      }}
    >
      {children}
    </ConversationContext.Provider>
  );
}

/**
 * Access conversation state from any component.
 * Must be used within a ConversationProvider.
 */
export function useConversation(): ConversationState {
  const ctx = useContext(ConversationContext);
  if (!ctx) {
    throw new Error(
      "useConversation must be used within a ConversationProvider"
    );
  }
  return ctx;
}
