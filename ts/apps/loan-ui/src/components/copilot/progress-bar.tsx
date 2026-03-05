/** Progress bar — 5-step tracker with numbered circles and connecting track. */

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
  /* Active-track width: fraction of the inter-circle span */
  const pct = ((Math.min(currentStep, STEPS.length - 1)) / (STEPS.length - 1)) * 100;

  return (
    <div className="bg-white border-b border-[#E2E6ED] px-5 py-3">
      <div className="max-w-[500px] mx-auto">
        {/* Track + circles row */}
        <div className="relative flex items-center justify-between">
          {/* Base track */}
          <div className="absolute inset-x-[13px] top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-[#E2E6ED]" />
          {/* Active track */}
          <div
            className="absolute left-[13px] top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-[#00A3B4] transition-all duration-500 ease-out"
            style={{ width: `calc(${pct}% * (100% - 26px) / 100%)` }}
          />
          {/* Step circles */}
          {STEPS.map((s, i) => {
            const done = i < currentStep;
            const active = i === currentStep;
            return (
              <div key={s.key} className="relative z-10 flex-shrink-0">
                <div
                  className="w-[26px] h-[26px] rounded-full flex items-center justify-center text-[11px] font-bold transition-all duration-300"
                  style={{
                    background: done ? "#00A3B4" : active ? "#002B5C" : "#EEF0F4",
                    color: done || active ? "#fff" : "#9BA4B4",
                    boxShadow: active ? "0 0 0 4px rgba(0,43,92,0.12)" : "none",
                  }}
                >
                  {done ? (
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Labels row */}
        <div className="flex justify-between mt-2">
          {STEPS.map((s, i) => (
            <div
              key={s.key}
              className="text-[9px] font-semibold uppercase tracking-wider transition-colors duration-300"
              style={{
                color:
                  i < currentStep
                    ? "#007A87"
                    : i === currentStep
                    ? "#002B5C"
                    : "#9BA4B4",
              }}
            >
              {s.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
