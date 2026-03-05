/**
 * Chat input — auto-growing textarea with send button.
 * Enter sends the message, Shift+Enter adds a newline.
 * Matches the SAG card aesthetic with subtle focus ring.
 */

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/utils";
import { ArrowUp } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Ask a question...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* Auto-resize textarea to content */
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  /* Focus input on mount */
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
        textareaRef.current.focus();
      }
    });
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div
      className={cn(
        "relative flex items-end gap-2",
        "bg-card border border-foreground/[0.08] rounded-2xl",
        "px-4 py-2.5",
        "shadow-[0_2px_12px_rgba(0,0,0,0.04)]",
        "focus-within:border-foreground/[0.15]",
        "focus-within:shadow-[0_2px_20px_rgba(0,0,0,0.07)]",
        "transition-all duration-200"
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={cn(
          "flex-1 resize-none bg-transparent",
          "text-[15px] text-foreground placeholder:text-foreground/30",
          "leading-relaxed py-1",
          "focus:outline-none",
          "disabled:opacity-50",
          "max-h-[200px]",
          "scrollbar-thin"
        )}
      />

      <button
        type="button"
        onClick={handleSend}
        disabled={!canSend}
        className={cn(
          "flex-shrink-0 h-9 w-9 rounded-xl",
          "flex items-center justify-center",
          "transition-all duration-200",
          canSend
            ? "bg-foreground text-background hover:bg-foreground/80 active:scale-95"
            : "bg-foreground/[0.06] text-foreground/20 cursor-not-allowed"
        )}
        aria-label="Send message"
      >
        <ArrowUp className="h-[18px] w-[18px]" strokeWidth={2} />
      </button>
    </div>
  );
}
