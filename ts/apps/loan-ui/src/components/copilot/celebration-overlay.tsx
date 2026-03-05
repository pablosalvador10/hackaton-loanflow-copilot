/** Celebration overlay — success screen after disbursement. */

import { useCopilot } from "@/hooks/use-copilot";
import { CheckCircle } from "lucide-react";

export function CelebrationOverlay() {
  const { showCelebration, offer } = useCopilot();
  if (!showCelebration) return null;

  const amount = offer?.amount || 150000;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center animate-fade-in bg-black/70 backdrop-blur-md">
      <div className="bg-white rounded-3xl shadow-2xl text-center px-8 py-10 max-w-sm mx-4 animate-scale-in">
        <div className="w-16 h-16 mx-auto mb-5 rounded-full bg-emerald-50 flex items-center justify-center">
          <CheckCircle className="w-8 h-8 text-emerald-600" />
        </div>

        <h2 className="text-xl font-bold text-[#1A2038] mb-1">Congratulations!</h2>
        <p className="text-sm text-[#6B7690] mb-6 leading-relaxed">
          Your financing has been approved and funds are being transferred.
        </p>

        <div className="bg-[#F8F9FC] rounded-2xl p-5 mb-6">
          <div className="text-[11px] text-[#8B95A9] uppercase tracking-wider font-medium mb-1">Amount Disbursed</div>
          <div className="text-3xl font-extrabold text-[#002B5C]">
            <span className="text-sm font-semibold text-[#8B95A9]">SAR </span>{amount.toLocaleString()}
          </div>
          <div className="text-xs text-[#8B95A9] mt-1">Account ending in ****4821</div>
        </div>

        <button onClick={() => window.location.reload()}
          className="w-full py-3.5 rounded-xl text-sm font-semibold text-white bg-[#002B5C] transition-all hover:bg-[#003A75] hover:-translate-y-px hover:shadow-lg active:scale-[0.98]">
          View Dashboard
        </button>
      </div>
    </div>
  );
}
