/** Chat screen — the main copilot conversation interface. */

import { useRef, useEffect, useState, useCallback } from "react";
import { useCopilot } from "@/hooks/use-copilot";
import { ProgressBar } from "./progress-bar";
import { CopilotMessage } from "./copilot-message";
import { TypingIndicator } from "./typing-indicator";
import { CelebrationOverlay } from "./celebration-overlay";
import { Send, ArrowUpRight } from "lucide-react";

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
    <div className="min-h-screen flex flex-col bg-[#F8F9FC]">
      {/* Top bar */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-6 h-14 bg-white border-b border-[#E8ECF2] shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#002B5C] flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4">
              <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="white" strokeWidth="1.5" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="1.5" />
              <path d="M2 12l10 5 10-5" stroke="white" strokeWidth="1.5" />
            </svg>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[#1A2038]">LOH Copilot</span>
            <span className="text-[9px] font-bold tracking-wider text-white px-1.5 py-0.5 rounded bg-gradient-to-r from-[#002B5C] to-[#004A8F]">AI</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setMode(mode === "mcp" ? "azure" : "mcp")}
            className="text-[10px] font-semibold px-3 py-1.5 rounded-lg transition-all duration-200 border"
            style={{
              background: mode === "azure" ? "#F0F0FF" : "#F0FAFB",
              borderColor: mode === "azure" ? "#D4D4FF" : "#CCE8EC",
              color: mode === "azure" ? "#5B21B6" : "#0E7490",
            }}
          >
            {mode === "azure" ? "Azure AI" : "MCP"}
          </button>
          <div className="w-8 h-8 rounded-lg bg-[#F0F2F5] text-[#5A6577] text-xs font-bold flex items-center justify-center">
            U
          </div>
        </div>
      </header>

      {/* Progress — only shown in scripted MCP mode */}
      {mode === "mcp" && <ProgressBar currentStep={currentStep} />}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth scrollbar-thin">
        <div className="max-w-2xl mx-auto space-y-5">
          {messages.map((msg, i) => (
            <CopilotMessage key={msg.id} message={msg} isLatest={i === messages.length - 1} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="sticky bottom-0 z-40 bg-white/95 backdrop-blur-xl border-t border-[#E8ECF2] px-4 sm:px-6 py-3">
        <div className="flex items-end gap-2 max-w-2xl mx-auto">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => { setInput(e.target.value); growTextarea(); }}
            onKeyDown={onKeyDown}
            placeholder="Type your message..."
            className="flex-1 resize-none px-4 py-3 rounded-xl text-sm text-[#1A2038] bg-[#F4F5F7] border border-transparent outline-none transition-all duration-200 leading-relaxed placeholder:text-[#A0A8B8] focus:bg-white focus:border-[#002B5C]/20 focus:ring-2 focus:ring-[#002B5C]/5"
            style={{ minHeight: "44px", maxHeight: "120px" }}
          />
          <button
            onClick={onSend}
            disabled={!hasText}
            className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-200 ${
              hasText
                ? "bg-[#002B5C] text-white shadow-md hover:bg-[#003A75] hover:-translate-y-px"
                : "bg-[#E8ECF2] text-[#A0A8B8] cursor-not-allowed"
            }`}
          >
            <ArrowUpRight className="w-[18px] h-[18px]" />
          </button>
        </div>
        <p className="text-center mt-2 text-[10px] text-[#B0B8C8]">
          Your data is encrypted & secure
        </p>
      </div>

      <CelebrationOverlay />
    </div>
  );
}
