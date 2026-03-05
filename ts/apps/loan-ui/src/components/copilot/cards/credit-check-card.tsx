/** Credit check animation card — 4 steps that animate sequentially. */

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

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
    <div className="bg-white rounded-2xl border border-[#E8ECF2] p-5 mt-3 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      {STEPS.map((label, i) => {
        const done = completed.includes(i);
        const visible = i === 0 || i <= Math.max(-1, ...completed) + 1;
        return (
          <div key={i}
            className={`flex items-center gap-3 py-2.5 transition-all duration-300 ${
              visible ? "opacity-100" : "opacity-0"
            }`}>
            <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
              done ? "bg-emerald-50 text-emerald-600" : "bg-[#F4F5F7] text-[#A0A8B8]"
            }`}>
              {done ? <Check className="w-3.5 h-3.5" /> : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            </div>
            <span className="text-[13px] font-medium text-[#1A2038] flex-1">{label}</span>
            <span className={`text-[11px] font-medium ${
              done ? "text-emerald-600" : "text-[#A0A8B8]"
            }`}>{done ? "Done" : "Pending"}</span>
          </div>
        );
      })}
    </div>
  );
}
