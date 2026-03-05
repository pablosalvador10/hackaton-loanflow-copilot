/**
 * Welcome screen — landing page matching AIConversational.html design.
 * Navy gradient background with CREALOGIX LOH branding.
 */

import { useCopilot } from "@/hooks/use-copilot";

const pills = [
  { icon: "💬", label: "Natural Language" },
  { icon: "☕", label: "Sharia Compliant" },
  { icon: "⚡", label: "Instant Decisions" },
  { icon: "🔒", label: "SAMA Regulated" },
];

export function WelcomeScreen() {
  const { startCopilot } = useCopilot();

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden"
      style={{ background: "linear-gradient(135deg, #002B5C 0%, #004080 50%, #00A3B4 100%)" }}>
      {/* Pattern overlay */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle at 20% 80%, rgba(0,163,180,0.1) 0%, transparent 50%), radial-gradient(circle at 80% 20%, rgba(255,255,255,0.03) 0%, transparent 50%)",
        }} />
      <div className="absolute -top-1/2 -right-[30%] w-[600px] h-[600px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(0,163,180,0.2) 0%, transparent 70%)" }} />

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col justify-center items-center px-6 py-10 text-center">
        {/* Logo */}
        <div className="mb-8 animate-fade-in-down">
          <div className="w-20 h-20 mx-auto mb-4 rounded-[20px] flex items-center justify-center border border-white/15"
            style={{ background: "rgba(255,255,255,0.12)", backdropFilter: "blur(10px)" }}>
            <svg viewBox="0 0 44 44" fill="none" className="w-11 h-11">
              <path d="M22 4L38 12V28L22 36L6 28V12L22 4Z" stroke="white" strokeWidth="2" fill="none" />
              <path d="M22 4L38 12L22 20L6 12L22 4Z" fill="rgba(255,255,255,0.2)" />
              <circle cx="22" cy="20" r="6" fill="rgba(0,212,232,0.6)" stroke="white" strokeWidth="1.5" />
              <path d="M19 20L21 22L25 18" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div className="text-[11px] font-bold tracking-[3px] uppercase" style={{ color: "#00C4D6" }}>CREALOGIX</div>
          <div className="text-[28px] font-extrabold text-white tracking-[3px]">LOH</div>
          <div className="text-[13px] text-white/60 tracking-[1.5px] mt-1">AI Lending Copilot</div>
        </div>

        {/* Hero */}
        <div className="mb-12 animate-fade-in-up">
          <h1 className="text-[32px] font-bold text-white leading-tight mb-4">
            Your AI Guide to <span style={{ color: "#00D4E8" }}>Smart Lending</span>
          </h1>
          <p className="text-base text-white/70 leading-relaxed max-w-[340px] mx-auto">
            Chat naturally with our AI Copilot to find the perfect Sharia-compliant financing solution — no forms, just a conversation.
          </p>
        </div>

        {/* Pills */}
        <div className="flex flex-wrap gap-2.5 justify-center mb-12 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
          {pills.map(p => (
            <div key={p.label} className="flex items-center gap-1.5 px-[18px] py-2 rounded-full text-[13px] text-white/90 border border-white/12"
              style={{ background: "rgba(255,255,255,0.1)", backdropFilter: "blur(10px)" }}>
              <span>{p.icon}</span> {p.label}
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="w-full max-w-[380px] animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
          <button onClick={startCopilot}
            className="w-full py-[18px] px-8 bg-white rounded-2xl text-[17px] font-bold flex items-center justify-center gap-2.5 transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_32px_rgba(0,0,0,0.2)]"
            style={{ color: "#002B5C", boxShadow: "0 4px 24px rgba(0,0,0,0.15)" }}>
            Start a Conversation
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Footer */}
      <div className="relative z-10 pb-6 text-center animate-fade-in-up" style={{ animationDelay: "0.6s" }}>
        <div className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-[11px] text-white/50 mb-2.5"
          style={{ background: "rgba(255,255,255,0.06)" }}>
          🏛 SAMA Licensed &amp; Regulated
        </div>
        <p className="text-xs text-white/40 leading-relaxed">
          Powered by <strong className="text-white/50">CREALOGIX</strong> LOH Platform<br />Sharia-compliant digital lending
        </p>
      </div>
    </div>
  );
}
