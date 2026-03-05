/** Chat screen — the main copilot conversation interface. */

import { useRef, useEffect, useState, useCallback } from "react";
import { useCopilot } from "@/hooks/use-copilot";
import { ProgressBar } from "./progress-bar";
import { CopilotMessage } from "./copilot-message";
import { TypingIndicator } from "./typing-indicator";
import { CelebrationOverlay } from "./celebration-overlay";

export function ChatScreen() {
  const { messages, currentStep, isTyping, handleSendMessage, mode, setMode } = useCopilot();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const hasText = input.trim().length > 0;

  /* Auto-scroll on new messages */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  /* Auto-grow textarea up to 120px */
  const growTextarea = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  }, []);

  const onSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    // Reset height after clearing
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    handleSendMessage(text);
  }, [input, handleSendMessage]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSend();
      }
    },
    [onSend]
  );

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#F4F6FA" }}>
      {/* Top bar */}
      <div
        className="sticky top-0 z-50 flex items-center justify-between px-5 h-[60px]"
        style={{ background: "#002B5C", borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="text-[10px] font-bold tracking-[2px]" style={{ color: "#00C4D6" }}>
            CREALOGIX
          </div>
          <div className="w-px h-5 bg-white/15" />
          <div className="text-[15px] font-semibold text-white flex items-center gap-2">
            LOH Copilot
            <span
              className="text-[9px] font-extrabold text-white px-2 py-0.5 rounded-md tracking-wider"
              style={{ background: "linear-gradient(135deg, #7C3AED, #A78BFA)" }}
            >
              AI
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Mode toggle */}
          <button
            onClick={() => setMode(mode === "mcp" ? "azure" : "mcp")}
            className="text-[10px] font-semibold px-2.5 py-1 rounded-md transition-all duration-200 hover:opacity-80"
            style={{
              background:
                mode === "azure"
                  ? "rgba(124,58,237,0.25)"
                  : "rgba(0,212,232,0.2)",
              color: mode === "azure" ? "#A78BFA" : "#00D4E8",
            }}
          >
            {mode === "azure" ? "AZURE AI" : "MCP DIRECT"}
          </button>
          <div
            className="w-[34px] h-[34px] rounded-[10px] flex items-center justify-center text-white text-sm font-bold"
            style={{ background: "rgba(255,255,255,0.12)" }}
          >
            MS
          </div>
        </div>
      </div>

      {/* Progress — only shown in scripted MCP mode */}
      {mode === "mcp" && <ProgressBar currentStep={currentStep} />}

      {/* Message list — subtle dot-grid background */}
      <div
        className="flex-1 overflow-y-auto px-5 py-6 scroll-smooth scrollbar-thin"
        style={{
          backgroundImage:
            "radial-gradient(circle, rgba(0,43,92,0.045) 1px, transparent 1px)",
          backgroundSize: "22px 22px",
        }}
      >
        <div className="max-w-[620px] mx-auto space-y-4">
          {messages.map((msg) => (
            <CopilotMessage key={msg.id} message={msg} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input bar */}
      <div
        className="sticky bottom-0 z-40 px-5 py-3"
        style={{
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          borderTop: "1px solid rgba(0,43,92,0.08)",
        }}
      >
        <div className="flex items-end gap-2.5 max-w-[620px] mx-auto">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              growTextarea();
            }}
            onKeyDown={onKeyDown}
            placeholder="Type your message… (Enter to send, Shift+Enter for new line)"
            className="flex-1 resize-none px-[18px] py-3 border-[1.5px] rounded-[14px] text-[15px] text-[#1A2038] outline-none transition-all duration-200 leading-relaxed placeholder:text-[#BFC6D2]"
            style={{
              fontFamily: "'Inter', sans-serif",
              borderColor: hasText ? "#002B5C" : "#E2E6ED",
              boxShadow: hasText
                ? "0 0 0 3px rgba(0,43,92,0.07)"
                : "none",
              minHeight: "48px",
              maxHeight: "120px",
            }}
          />
          <button
            onClick={onSend}
            disabled={!hasText}
            className="w-12 h-12 rounded-[14px] text-white flex items-center justify-center flex-shrink-0 transition-all duration-200"
            style={{
              background: hasText
                ? "linear-gradient(135deg, #002B5C 0%, #004080 100%)"
                : "#DDE2EA",
              transform: hasText ? "translateY(-1px)" : "none",
              boxShadow: hasText
                ? "0 4px 14px rgba(0,43,92,0.28)"
                : "none",
              cursor: hasText ? "pointer" : "default",
            }}
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-5 h-5 transition-transform duration-150"
              style={{ transform: hasText ? "rotate(-45deg)" : "none" }}
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="text-center mt-2 text-[11px] text-[#B0B8C8] max-w-[620px] mx-auto">
          Powered by LOH AI Copilot · Your data is encrypted &amp; secure
        </div>
      </div>

      <CelebrationOverlay />
    </div>
  );
}
