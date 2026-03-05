/**
 * Welcome screen — clean, professional landing for LOH AI Lending Copilot.
 */

import { useCopilot } from "@/hooks/use-copilot";
import { MessageSquare, Shield, Zap, CheckCircle } from "lucide-react";
import type { ReactNode } from "react";

const features: { icon: ReactNode; label: string; desc: string }[] = [
  { icon: <MessageSquare className="w-5 h-5" />, label: "Conversational", desc: "Chat in natural language" },
  { icon: <Shield className="w-5 h-5" />, label: "Sharia Compliant", desc: "Certified by Sharia board" },
  { icon: <Zap className="w-5 h-5" />, label: "Instant Decisions", desc: "Real-time credit analysis" },
  { icon: <CheckCircle className="w-5 h-5" />, label: "SAMA Regulated", desc: "Licensed & secure" },
];

export function WelcomeScreen() {
  const { startCopilot } = useCopilot();

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFBFD] relative overflow-hidden">
      {/* Subtle background decoration */}
      <div className="absolute top-0 left-0 right-0 h-[480px] bg-gradient-to-b from-[#002B5C] via-[#003A75] to-transparent" />
      <div className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full opacity-[0.06] pointer-events-none"
        style={{ background: "radial-gradient(circle, #00A3B4, transparent 70%)", transform: "translate(30%, -40%)" }} />

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col">
        {/* Header */}
        <header className="flex items-center gap-3 px-8 pt-8 pb-4">
          <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-sm border border-white/10 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
              <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="white" strokeWidth="1.5" />
              <path d="M2 17l10 5 10-5" stroke="white" strokeWidth="1.5" />
              <path d="M2 12l10 5 10-5" stroke="white" strokeWidth="1.5" />
            </svg>
          </div>
          <div>
            <div className="text-[10px] font-semibold tracking-[2.5px] uppercase text-white/50">CREALOGIX</div>
            <div className="text-lg font-bold text-white tracking-wide leading-none">LOH</div>
          </div>
        </header>

        {/* Hero area */}
        <div className="flex-1 flex flex-col items-center justify-center px-6 pb-8">
          <div className="max-w-lg w-full text-center mb-10 animate-fade-in-down">
            <div className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-6 text-xs font-medium text-[#00D4E8] bg-white/[0.08] border border-white/[0.08] backdrop-blur-sm">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00D4E8] animate-pulse" />
              AI-Powered Lending Platform
            </div>
            <h1 className="text-4xl sm:text-5xl font-extrabold text-white leading-[1.1] mb-4 tracking-tight">
              Smart Lending,<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4E8] to-[#00A3B4]">Made Simple</span>
            </h1>
            <p className="text-base text-white/60 leading-relaxed max-w-sm mx-auto">
              Find the perfect Sharia-compliant financing through a simple conversation — no forms required.
            </p>
          </div>

          {/* Feature grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-xl w-full mb-10 animate-fade-in-up"
            style={{ animationDelay: "0.15s", animationFillMode: "both" }}>
            {features.map((f) => (
              <div key={f.label}
                className="flex flex-col items-center gap-2 rounded-2xl px-4 py-5 bg-white border border-[#E8ECF2] shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
                <div className="w-10 h-10 rounded-xl bg-[#F0F7FF] text-[#002B5C] flex items-center justify-center">
                  {f.icon}
                </div>
                <div className="text-xs font-semibold text-[#1A2038]">{f.label}</div>
                <div className="text-[10px] text-[#8B95A9] leading-snug text-center">{f.desc}</div>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="w-full max-w-sm animate-fade-in-up" style={{ animationDelay: "0.3s", animationFillMode: "both" }}>
            <button
              onClick={startCopilot}
              className="w-full py-4 px-8 rounded-2xl text-base font-semibold flex items-center justify-center gap-3 group transition-all duration-200 hover:-translate-y-0.5 active:scale-[0.98] text-white shadow-[0_4px_24px_rgba(0,43,92,0.3)] hover:shadow-[0_8px_32px_rgba(0,43,92,0.4)]"
              style={{ background: "linear-gradient(135deg, #002B5C 0%, #004A8F 100%)" }}
            >
              Start a Conversation
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                className="transition-transform duration-200 group-hover:translate-x-0.5">
                <path d="M5 12h14" /><path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="relative z-10 pb-6 pt-4 text-center border-t border-[#E8ECF2]">
          <p className="text-[11px] text-[#8B95A9]">
            SAMA Licensed & Regulated · Powered by <span className="font-semibold text-[#6B7690]">CREALOGIX</span> LOH Platform
          </p>
        </footer>
      </div>
    </div>
  );
}
