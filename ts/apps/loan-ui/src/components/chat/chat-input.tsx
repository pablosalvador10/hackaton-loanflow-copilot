/**
 * Chat input — auto-growing textarea with send button and file attachment.
 * Enter sends the message, Shift+Enter adds a newline.
 * Includes an optional file upload button for document attachments.
 */

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/utils";
import { ArrowUp, Paperclip } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileSelect?: (file: File) => void;
  disabled?: boolean;
  placeholder?: string;
  hasPendingDocument?: boolean;
}

export function ChatInput({
  onSend,
  onFileSelect,
  disabled = false,
  placeholder = "Describe your loan needs or upload a document…",
  hasPendingDocument = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && onFileSelect) {
        onFileSelect(file);
      }
      // Reset the input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [onFileSelect]
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
      {/* File upload button */}
      {onFileSelect && (
        <>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp"
            onChange={handleFileChange}
            className="hidden"
            aria-label="Upload document"
          />
          <button
            type="button"
            onClick={handleFileClick}
            disabled={disabled}
            className={cn(
              "flex-shrink-0 h-9 w-9 rounded-xl",
              "flex items-center justify-center",
              "transition-all duration-200",
              hasPendingDocument
                ? "bg-primary/10 text-primary border border-primary/20"
                : "bg-foreground/[0.04] text-foreground/30 hover:text-foreground/50 hover:bg-foreground/[0.08]",
              disabled && "opacity-50 cursor-not-allowed"
            )}
            aria-label="Attach document"
            title={hasPendingDocument ? "Document attached" : "Upload a document"}
          >
            <Paperclip className="h-[16px] w-[16px]" strokeWidth={1.5} />
          </button>
        </>
      )}

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
