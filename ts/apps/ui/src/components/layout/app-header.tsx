/**
 * App header — VIN Insight branding with New Chat and conversation history.
 * No authentication required.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useConversation } from "@/hooks/use-conversation";
import {
  Car,
  Plus,
  Clock,
} from "lucide-react";

/** Produce a human-friendly relative timestamp such as "2 min ago". */
function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString();
}

export function AppHeader() {
  const [historyOpen, setHistoryOpen] = useState(false);
  const historyRef = useRef<HTMLDivElement>(null);
  const { clearConversation, messages, conversations, loadConversation, conversationId } =
    useConversation();

  /* Close history dropdown on outside click */
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        historyRef.current &&
        !historyRef.current.contains(e.target as Node)
      ) {
        setHistoryOpen(false);
      }
    }
    if (historyOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [historyOpen]);

  const handleNewChat = useCallback(() => {
    clearConversation();
  }, [clearConversation]);

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-40",
        "flex items-center justify-between",
        "px-4 md:px-6 lg:px-8",
        "h-[60px] md:h-[64px]",
        "bg-background/70 backdrop-blur-md",
        "border-b border-foreground/[0.04]"
      )}
    >
      {/* Logo — left side */}
      <div className="flex items-center gap-2.5">
        <div
          className={cn(
            "h-8 w-8 rounded-lg",
            "bg-primary/[0.08] border border-primary/15",
            "flex items-center justify-center"
          )}
        >
          <Car
            className="h-4 w-4 text-primary"
            strokeWidth={1.5}
          />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-foreground leading-tight">
            VIN Insight
          </span>
          <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-foreground/30 leading-tight hidden sm:block">
            Fleet Vehicle Intelligence
          </span>
        </div>
      </div>

      {/* Right side — History + New Chat */}
      <div className="flex items-center gap-2">
        {/* Conversation history — visible when there are saved conversations */}
        {conversations.length > 0 && (
          <div className="relative" ref={historyRef}>
            <button
              onClick={() => setHistoryOpen(!historyOpen)}
              className={cn(
                "flex items-center gap-1.5",
                "h-8 px-3 rounded-lg",
                "text-xs font-medium text-foreground/50",
                "border border-foreground/[0.08]",
                "hover:text-foreground/70 hover:bg-foreground/[0.03]",
                "hover:border-foreground/[0.12]",
                "active:scale-[0.97]",
                "transition-all duration-200"
              )}
              aria-label="Conversation history"
              aria-expanded={historyOpen}
            >
              <Clock className="h-3.5 w-3.5" strokeWidth={1.5} />
              <span className="hidden sm:inline">History</span>
            </button>

            {historyOpen && (
              <div
                className={cn(
                  "absolute right-0 top-full mt-2",
                  "w-72 max-h-80 rounded-xl overflow-hidden",
                  "bg-background/95 backdrop-blur-xl",
                  "border border-foreground/[0.08]",
                  "shadow-[0_8px_30px_rgba(0,0,0,0.12)]",
                  "animate-fade-in opacity-0",
                  "z-50 flex flex-col"
                )}
              >
                <div className="px-4 py-3 border-b border-foreground/[0.06]">
                  <p className="text-xs font-semibold text-foreground/60 uppercase tracking-wider">
                    Recent lookups
                  </p>
                </div>
                <div className="overflow-y-auto flex-1 p-1.5 space-y-0.5">
                  {conversations.map((conv) => (
                    <button
                      key={conv.id}
                      onClick={() => {
                        loadConversation(conv.id);
                        setHistoryOpen(false);
                      }}
                      className={cn(
                        "w-full flex flex-col gap-0.5 px-3.5 py-2.5 rounded-lg text-left",
                        "hover:bg-foreground/[0.05] transition-colors duration-150",
                        conv.id === conversationId &&
                          "bg-primary/[0.06] border border-primary/10"
                      )}
                    >
                      <span
                        className={cn(
                          "text-sm truncate w-full",
                          conv.id === conversationId
                            ? "text-primary font-medium"
                            : "text-foreground/70"
                        )}
                      >
                        {conv.title}
                      </span>
                      <span className="text-[10px] text-foreground/30">
                        {formatRelativeTime(conv.updatedAt)} ·{" "}
                        {conv.messages.length} message
                        {conv.messages.length !== 1 ? "s" : ""}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* New Chat button — only visible when there are messages */}
        {messages.length > 0 && (
          <button
            onClick={handleNewChat}
            className={cn(
              "flex items-center gap-1.5",
              "h-8 px-3 rounded-lg",
              "text-xs font-medium text-foreground/50",
              "border border-foreground/[0.08]",
              "hover:text-foreground/70 hover:bg-foreground/[0.03]",
              "hover:border-foreground/[0.12]",
              "active:scale-[0.97]",
              "transition-all duration-200"
            )}
          >
            <Plus className="h-3.5 w-3.5" strokeWidth={1.5} />
            <span className="hidden sm:inline">New Lookup</span>
          </button>
        )}
      </div>
    </header>
  );
}
