/** Progress bar — 5-step tracker with clean pill design. */

import type { ProgressStep } from "@/types";
import { Check } from "lucide-react";

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
    <div className="bg-white border-b border-[#E8ECF2] px-4 sm:px-6 py-3">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-1">
          {STEPS.map((s, i) => {
            const done = i < currentStep;
            const active = i === currentStep;
            return (
              <div key={s.key} className="flex items-center flex-1 last:flex-none">
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all duration-300 ${
                  done
                    ? "text-emerald-700 bg-emerald-50"
                    : active
                      ? "text-[#002B5C] bg-[#F0F4FA] font-semibold"
                      : "text-[#A0A8B8]"
                }`}>
                  {done ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <span className={`w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center ${
                      active ? "bg-[#002B5C] text-white" : "bg-[#E8ECF2] text-[#A0A8B8]"
                    }`}>{i + 1}</span>
                  )}
                  {s.label}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-px mx-1 transition-colors duration-300 ${
                    done ? "bg-emerald-300" : "bg-[#E8ECF2]"
                  }`} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
