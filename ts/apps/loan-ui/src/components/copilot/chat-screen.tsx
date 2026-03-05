/** Chat screen — the main copilot conversation interface. */

import { useRef, useEffect, useState } from "react";
import { useCopilot } from "@/hooks/use-copilot";
import { ProgressBar } from "./progress-bar";
import { CopilotMessage } from "./copilot-message";
import { TypingIndicator } from "./typing-indicator";
import { CelebrationOverlay } from "./celebration-overlay";

export function ChatScreen() {
  const { messages, currentStep, isTyping, handleSendMessage, mode, setMode } = useCopilot();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const onSend = () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    handleSendMessage(text);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "#F7F9FC" }}>
      {/* Top bar */}
      <div className="sticky top-0 z-50 flex items-center justify-between px-5 h-[60px]"
        style={{ background: "#002B5C" }}>
        <div className="flex items-center gap-2.5">
          <div className="text-[10px] font-bold tracking-[2px]" style={{ color: "#00C4D6" }}>CREALOGIX</div>
          <div className="w-px h-5 bg-white/15" />
          <div className="text-[15px] font-semibold text-white flex items-center gap-2">
            LOH Copilot
            <span className="text-[9px] font-extrabold text-white px-2 py-0.5 rounded-md tracking-wider"
              style={{ background: "linear-gradient(135deg, #7C3AED, #A78BFA)" }}>AI</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Mode toggle */}
          <button onClick={() => setMode(mode === "mcp" ? "azure" : "mcp")}
            className="text-[10px] font-semibold px-2.5 py-1 rounded-md transition-all"
            style={{
              background: mode === "azure" ? "rgba(124,58,237,0.25)" : "rgba(0,212,232,0.2)",
              color: mode === "azure" ? "#A78BFA" : "#00D4E8",
            }}>
            {mode === "azure" ? "AZURE AI" : "MCP DIRECT"}
          </button>
          <div className="w-[34px] h-[34px] rounded-[10px] flex items-center justify-center text-white text-sm font-bold"
            style={{ background: "rgba(255,255,255,0.12)" }}>
            MS
          </div>
        </div>
      </div>

      {/* Progress — only shown in scripted MCP mode */}
      {mode === "mcp" && <ProgressBar currentStep={currentStep} />}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 scroll-smooth">
        <div className="max-w-[600px] mx-auto space-y-5">
          {messages.map(msg => (
            <CopilotMessage key={msg.id} message={msg} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="sticky bottom-0 z-40 bg-white border-t border-[#E2E6ED] px-5 py-4">
        <div className="flex items-center gap-2.5 max-w-[600px] mx-auto">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && onSend()}
            placeholder="Type your message..."
            className="flex-1 px-[18px] py-3.5 border-[1.5px] border-[#E2E6ED] rounded-[14px] text-[15px] text-[#1A2038] outline-none transition-all
              focus:border-[#002B5C] focus:shadow-[0_0_0_3px_rgba(0,43,92,0.06)] placeholder:text-[#BFC6D2]"
            style={{ fontFamily: "'Inter', sans-serif" }}
          />
          <button onClick={onSend}
            className="w-12 h-12 rounded-[14px] text-white flex items-center justify-center flex-shrink-0 transition-all hover:-translate-y-px hover:shadow-[0_4px_12px_rgba(0,43,92,0.2)]"
            style={{ background: "linear-gradient(135deg, #002B5C 0%, #004080 100%)" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div className="text-center mt-2 text-[11px] text-[#9BA4B4] max-w-[600px] mx-auto">
          Powered by LOH AI Copilot · Your data is encrypted &amp; secure
        </div>
      </div>

      <CelebrationOverlay />
    </div>
  );
}
