/** Progress bar — 5-step tracker matching the HTML design. */

import type { ProgressStep } from "@/types";

const STEPS: { key: ProgressStep; label: string }[] = [
  { key: "identity", label: "Identity" },
  { key: "needs", label: "Needs" },
  { key: "product", label: "Product" },
  { key: "approval", label: "Approval" },
  { key: "contract", label: "Contract" },
];

interface Props {
  currentStep: number;
}

export function ProgressBar({ currentStep }: Props) {
  return (
    <div className="bg-white px-5 py-4 border-b border-[#E2E6ED]">
      <div className="flex items-center gap-1 max-w-[500px] mx-auto">
        {STEPS.map((_, i) => (
          <div key={i} className={`flex-1 h-1 rounded-sm transition-all duration-500 ${
            i < currentStep ? "bg-[#00A3B4]"
              : i === currentStep ? "bg-gradient-to-r from-[#00A3B4] to-[#00C4D6] animate-pulse" : "bg-[#DDE2EA]"
          }`} />
        ))}
      </div>
      <div className="flex justify-between mt-2 max-w-[500px] mx-auto">
        {STEPS.map((s, i) => (
          <div key={s.key} className={`text-[9px] font-semibold uppercase tracking-wider text-center flex-1 ${
            i < currentStep ? "text-[#007A87]"
              : i === currentStep ? "text-[#002B5C] font-bold" : "text-[#9BA4B4]"
          }`}>{s.label}</div>
        ))}
      </div>
    </div>
  );
}
