/**
 * Chat message — renders a single user or assistant message.
 *
 * User messages: right-aligned, dark background.
 * Bot messages: left-aligned, avatar + clean markdown body.
 */

import { cn } from "@/lib/utils";
import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "@/types";
import type { Components } from "react-markdown";

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ── Custom markdown components ── */

const markdownComponents: Components = {
  h1: ({ children }) => (
    <h3 className="text-lg font-semibold text-foreground mt-4 mb-2 first:mt-0">
      {children}
    </h3>
  ),
  h2: ({ children }) => (
    <h4 className="text-base font-semibold text-foreground mt-3.5 mb-1.5 first:mt-0">
      {children}
    </h4>
  ),
  h3: ({ children }) => (
    <h5 className="text-[15px] font-semibold text-foreground mt-3 mb-1 first:mt-0">
      {children}
    </h5>
  ),
  p: ({ children }) => (
    <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 last:mb-0 space-y-1.5 pl-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 last:mb-0 space-y-1.5 pl-1 list-decimal list-inside marker:text-foreground/30">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="flex gap-2 text-[15px] leading-relaxed">
      <span className="text-primary/50 select-none mt-0.5 flex-shrink-0">•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-primary hover:text-primary/80 underline underline-offset-2 decoration-primary/30 hover:decoration-primary/60 transition-colors"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.includes("language-");
    if (isBlock) {
      const lang = className?.replace("language-", "") ?? "";
      return (
        <div className="relative my-3 group">
          {lang && (
            <div className="absolute top-0 left-0 px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-foreground/25 bg-foreground/[0.03] rounded-tl-lg rounded-br-lg border-b border-r border-foreground/[0.06]">
              {lang}
            </div>
          )}
          <pre className="bg-foreground/[0.03] border border-foreground/[0.06] rounded-xl px-4 py-3.5 pt-8 overflow-x-auto">
            <code className="text-[13px] font-mono leading-relaxed text-foreground/75">
              {children}
            </code>
          </pre>
        </div>
      );
    }
    return (
      <code className="px-1.5 py-0.5 rounded-md bg-foreground/[0.05] text-[13px] font-mono text-foreground/75 border border-foreground/[0.04]">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <>{children}</>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-primary/30 pl-4 my-3 text-foreground/60 italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-4 border-foreground/[0.06]" />,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto rounded-lg border border-foreground/[0.06]">
      <table className="w-full text-[13px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-foreground/[0.03] border-b border-foreground/[0.06]">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left font-medium text-foreground/60 text-[12px] uppercase tracking-wider">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 border-t border-foreground/[0.04] text-foreground/70">
      {children}
    </td>
  ),
};

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3",
        "animate-fade-in-up opacity-0",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {/* Bot avatar */}
      {!isUser && (
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
      )}

      {/* Message bubble */}
      <div
        className={cn(
          "rounded-2xl",
          isUser
            ? "max-w-[85%] sm:max-w-[70%] bg-foreground text-background rounded-br-md px-4 py-3"
            : "max-w-[90%] sm:max-w-[80%] rounded-bl-md px-1"
        )}
      >
        <div
          className={cn(
            "text-[15px] leading-[1.7]",
            isUser ? "text-background/90" : "text-foreground/75"
          )}
        >
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Timestamp */}
        <p
          className={cn(
            "text-[10px] mt-2",
            isUser ? "text-background/30 text-right" : "text-foreground/20"
          )}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>

      {/* User avatar */}
      {isUser && (
        <div
          className={cn(
            "flex-shrink-0 h-8 w-8 rounded-full",
            "bg-foreground/[0.08] text-foreground/50",
            "flex items-center justify-center",
            "border border-foreground/[0.08]",
            "mt-0.5"
          )}
        >
          <User className="h-4 w-4" strokeWidth={1.5} />
        </div>
      )}
    </div>
  );
}
