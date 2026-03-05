/** Credit check animation card — 4 steps that animate sequentially. */

import { useEffect, useState } from "react";

const STEPS = [
  "Verifying identity with SIMAH",
  "Checking credit bureau records",
  "Analyzing income & obligations",
  "Calculating risk assessment",
];

export function CreditCheckCard() {
  const [completed, setCompleted] = useState<number[]>([]);

  useEffect(() => {
    STEPS.forEach((_, i) => {
      setTimeout(() => setCompleted(prev => [...prev, i]), 800 + i * 900);
    });
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-[#E2E6ED] p-6 mt-3 shadow-sm">
      {STEPS.map((label, i) => {
        const done = completed.includes(i);
        return (
          <div key={i}
            className={`flex items-center gap-3 py-2.5 transition-opacity duration-400 ${
              completed.length > 0 && i <= Math.max(...completed) ? "opacity-100" : i === 0 ? "opacity-100" : "opacity-0"
            }`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[13px] flex-shrink-0 ${
              done ? "bg-[#E8F8F2] text-[#00B880]" : "bg-[#EEF1F6] text-[#9BA4B4]"
            }`}>
              {done ? "✔" : "⏳"}
            </div>
            <div className="text-[13px] font-medium text-[#1A2038]">{label}</div>
            <div className={`ml-auto text-[11px] font-semibold ${done ? "text-[#00B880]" : "text-[#9BA4B4]"}`}>
              {done ? "Done" : "Pending"}
            </div>
          </div>
        );
      })}
    </div>
  );
}
