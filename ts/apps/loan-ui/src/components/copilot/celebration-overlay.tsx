/** Celebration overlay — success screen after disbursement. */

import { useCopilot } from "@/hooks/use-copilot";

export function CelebrationOverlay() {
  const { showCelebration, offer } = useCopilot();
  if (!showCelebration) return null;

  const amount = offer?.amount || 150000;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center animate-fade-in"
      style={{ background: "rgba(0,20,40,0.85)", backdropFilter: "blur(8px)" }}>
      <div className="text-center text-white px-6 py-10 max-w-[400px]">
        {/* Check icon */}
        <div className="w-[100px] h-[100px] mx-auto mb-6 rounded-full flex items-center justify-center animate-scale-in"
          style={{ background: "linear-gradient(135deg, #00B880 0%, #00D4A0 100%)", boxShadow: "0 8px 32px rgba(0,184,128,0.3)" }}>
          <svg viewBox="0 0 48 48" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="w-12 h-12">
            <polyline points="14 24 22 32 34 16" />
          </svg>
        </div>

        <h2 className="text-[26px] font-extrabold mb-2">Congratulations!</h2>
        <p className="text-[15px] text-white/70 mb-8 leading-relaxed">
          Your financing has been approved and funds are being transferred to your account.
        </p>

        <div className="text-[42px] font-extrabold mb-1">
          <span className="text-xl text-white/50">SAR </span>{amount.toLocaleString()}
        </div>
        <div className="text-[13px] text-white/45 mb-8">Disbursed to account ending in •••4821</div>

        <button onClick={() => window.location.reload()}
          className="w-full py-[18px] bg-white rounded-2xl text-[17px] font-bold transition-all hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.2)]"
          style={{ color: "#002B5C" }}>
          View Dashboard
        </button>
      </div>
    </div>
  );
}
