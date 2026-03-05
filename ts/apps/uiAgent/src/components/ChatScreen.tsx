/** Chat screen — free-form AI chat connected to loan.py + MCP servers. */

import { useState, useRef, useEffect, useCallback } from "react";
import { streamChat } from "../api";

interface Msg {
  id: string;
  role: "user" | "assistant";
  text: string;
}

export function ChatScreen() {
  const [messages, setMessages] = useState<Msg[]>([
    { id: "welcome", role: "assistant", text: "Welcome to LOH! I'm your AI Lending Copilot. Ask me anything about financing, loan applications, or Sharia-compliant products. How can I help you today? 👋" },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const convId = useRef(crypto.randomUUID());
  const historyRef = useRef<{ role: string; content: string }[]>([]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isTyping) return;
    const userMsg: Msg = { id: crypto.randomUUID(), role: "user", text };
    setMessages(prev => [...prev, userMsg]);
    historyRef.current.push({ role: "user", content: text });
    setInput("");
    setIsTyping(true);

    const botId = crypto.randomUUID();
    setMessages(prev => [...prev, { id: botId, role: "assistant", text: "" }]);

    await streamChat(
      {
        conversation_id: convId.current,
        message_id: crypto.randomUUID(),
        message: text,
        history: historyRef.current.slice(0, -1),
        application_id: null,
        document_context: null,
      },
      {
        onDelta: (chunk) => {
          setMessages(prev =>
            prev.map(m => m.id === botId ? { ...m, text: m.text + chunk } : m)
          );
        },
        onDone: () => {
          setIsTyping(false);
          setMessages(prev => {
            const bot = prev.find(m => m.id === botId);
            if (bot) historyRef.current.push({ role: "assistant", content: bot.text });
            return prev;
          });
        },
        onError: (msg) => {
          setIsTyping(false);
          setMessages(prev =>
            prev.map(m => m.id === botId ? { ...m, text: m.text || `Error: ${msg}` } : m)
          );
        },
      },
    );
  }, [isTyping]);

  const onSend = () => { send(input); };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#F7F9FC" }}>

      {/* Top bar */}
      <div style={{
        background: "#002B5C", padding: "0 20px", display: "flex",
        alignItems: "center", justifyContent: "space-between", height: 60,
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#00C4D6", letterSpacing: 2 }}>CREALOGIX</div>
          <div style={{ width: 1, height: 20, background: "rgba(255,255,255,0.15)" }} />
          <div style={{ fontSize: 15, fontWeight: 600, color: "#fff", display: "flex", alignItems: "center", gap: 8 }}>
            LOH Copilot
            <span style={{
              background: "linear-gradient(135deg, #7C3AED, #A78BFA)",
              fontSize: 9, fontWeight: 800, color: "#fff", padding: "3px 8px",
              borderRadius: 6, letterSpacing: 1,
            }}>AI</span>
          </div>
        </div>
        <div style={{
          width: 34, height: 34, background: "rgba(255,255,255,0.12)",
          borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontSize: 14, fontWeight: 700,
        }}>MS</div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: 20, scrollBehavior: "smooth" }}>
        <div style={{ maxWidth: 600, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
          {messages.map(m => (
            <div key={m.id} style={{
              display: "flex", gap: 12, animation: "msgIn 0.4s ease-out",
              flexDirection: m.role === "user" ? "row-reverse" : "row",
            }}>
              {/* Avatar */}
              <div style={{
                width: 36, height: 36, borderRadius: 12, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, fontWeight: 700,
                ...(m.role === "assistant"
                  ? { background: "linear-gradient(135deg, #002B5C, #00A3B4)", color: "#fff" }
                  : { background: "#DDE2EA", color: "#5A6577" }),
              }}>
                {m.role === "assistant" ? (
                  <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2}>
                    <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                  </svg>
                ) : "MS"}
              </div>
              {/* Bubble */}
              <div style={{
                maxWidth: "80%", padding: "14px 18px", borderRadius: 18,
                fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word",
                ...(m.role === "assistant"
                  ? { background: "#fff", color: "#1A2038", border: "1px solid #E2E6ED", borderBottomLeftRadius: 6, boxShadow: "0 1px 4px rgba(0,0,0,0.04)" }
                  : { background: "linear-gradient(135deg, #002B5C 0%, #004080 100%)", color: "#fff", borderBottomRightRadius: 6 }),
              }}
                dangerouslySetInnerHTML={{ __html: m.text }}
              />
            </div>
          ))}
          {isTyping && (
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 12, flexShrink: 0,
                background: "linear-gradient(135deg, #002B5C, #00A3B4)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <svg width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth={2}>
                  <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div style={{
                background: "#fff", border: "1px solid #E2E6ED", borderRadius: 18,
                borderBottomLeftRadius: 6, padding: "14px 18px", display: "flex", gap: 4,
              }}>
                {[0, 0.2, 0.4].map((d, i) => (
                  <div key={i} style={{
                    width: 8, height: 8, background: "#9BA4B4", borderRadius: "50%",
                    animation: `typingBounce 1.4s ease-in-out ${d}s infinite`,
                  }} />
                ))}
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* Input */}
      <div style={{
        background: "#fff", borderTop: "1px solid #E2E6ED", padding: "16px 20px",
        position: "sticky", bottom: 0, zIndex: 40,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, maxWidth: 600, margin: "0 auto" }}>
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && onSend()}
            placeholder="Type your message..."
            style={{
              flex: 1, padding: "14px 18px", border: "1.5px solid #E2E6ED",
              borderRadius: 14, fontSize: 15, fontFamily: "'Inter', sans-serif",
              color: "#1A2038", outline: "none",
            }}
          />
          <button onClick={onSend} style={{
            width: 48, height: 48, background: "linear-gradient(135deg, #002B5C 0%, #004080 100%)",
            border: "none", borderRadius: 14, color: "#fff", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={20} height={20}>
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
        <div style={{ textAlign: "center", marginTop: 8, fontSize: 11, color: "#9BA4B4", maxWidth: 600, margin: "8px auto 0" }}>
          Powered by LOH AI Copilot · Your data is encrypted &amp; secure
        </div>
      </div>
    </div>
  );
}
