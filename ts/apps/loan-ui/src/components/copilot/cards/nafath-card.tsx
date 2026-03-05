/** Nafath verification card — shows code with waiting animation. */

import { useState, useEffect } from "react";
import { Fingerprint, CheckCircle } from "lucide-react";

export function NafathCard() {
  const [approved, setApproved] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setApproved(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-[#E8ECF2] p-6 mt-3 text-center shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="w-10 h-10 mx-auto mb-3 rounded-xl bg-[#F0F4FA] flex items-center justify-center">
        <Fingerprint className="w-5 h-5 text-[#002B5C]" />
      </div>
      <div className="text-3xl font-extrabold tracking-[6px] text-[#002B5C] my-2">47</div>
      <div className="text-xs text-[#6B7690] mb-3">Match this number in your Nafath app</div>
      {approved ? (
        <div className="flex items-center justify-center gap-2 py-1.5 text-emerald-600 animate-slide-in-up">
          <CheckCircle className="w-4 h-4" />
          <span className="text-[13px] font-semibold">Approved</span>
        </div>
      ) : (
        <>
          <div className="flex gap-1.5 justify-center py-1">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-[#002B5C]/30 animate-pulse-dot" style={{ animationDelay: `${i * 200}ms` }} />
            ))}
          </div>
          <div className="text-[10px] text-[#8B95A9] mt-1.5">Waiting for approval...</div>
        </>
      )}
    </div>
  );
}
