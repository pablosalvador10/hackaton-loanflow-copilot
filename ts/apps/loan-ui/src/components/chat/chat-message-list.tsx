/**
 * Chat message list — scrollable container with auto-scroll.
 * Shows the empty state when there are no messages,
 * or the message thread + typing indicator when active.
 */

import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Bot } from "lucide-react";
import { ChatMessage } from "./chat-message";
import { ChatEmptyState } from "./chat-empty-state";
import { TypingIndicator } from "./typing-indicator";
import type { ChatMessage as ChatMessageType } from "@/types";

interface ChatMessageListProps {
  messages: ChatMessageType[];
  isLoading: boolean;
  onPromptClick: (prompt: string) => void;
}

export function ChatMessageList({
  messages,
  isLoading,
  onPromptClick,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll to bottom on new messages or loading change */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isLoading]);

  /* Hide typing indicator once the bot message has streamed content */
  const lastMsg = messages[messages.length - 1];
  const hasPendingAssistantPlaceholder =
    !!lastMsg &&
    lastMsg.role === "assistant" &&
    lastMsg.content.trim().length === 0;

  const showTyping =
    isLoading &&
    (!lastMsg || lastMsg.role === "user" || hasPendingAssistantPlaceholder);

  /* Empty state */
  if (messages.length === 0 && !isLoading) {
    return <ChatEmptyState onPromptClick={onPromptClick} />;
  }

  return (
    <div
      className={cn(
        "flex-1 overflow-y-auto",
        "px-4 py-6",
        "scrollbar-thin"
      )}
    >
      <div className="max-w-3xl mx-auto space-y-5">
        {messages
          .filter(
            (msg) =>
              !(
                isLoading &&
                msg.id === lastMsg?.id &&
                msg.role === "assistant" &&
                msg.content.trim().length === 0
              )
          )
          .map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

        {/* Typing indicator — only before first streamed token */}
        {showTyping && (
          <div className="flex gap-3 animate-fade-in opacity-0">
            <div
              className={cn(
                "flex-shrink-0 h-8 w-8 rounded-full",
                "bg-primary/[0.08] text-primary",
                "flex items-center justify-center",
                "border border-primary/15",
                "mt-0.5"
              )}
            >
              <Bot className="h-4 w-4" strokeWidth={1.5} />
            </div>
            <div
              className={cn(
                "rounded-2xl rounded-bl-md",
                "bg-card border border-foreground/[0.06]"
              )}
            >
              <TypingIndicator />
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
