/** Credit score card — animated ring with SIMAH score. */

import { useEffect, useRef } from "react";

interface Props {
  data?: Record<string, unknown>;
}

export function CreditScoreCard({ data }: Props) {
  const score = (data as { score?: number })?.score || 742;
  const rating = (data as { rating?: string })?.rating || "Excellent";
  const ringRef = useRef<SVGCircleElement>(null);

  const circumference = 2 * Math.PI * 50;
  const pct = Math.min((score - 300) / 600, 1);
  const offset = circumference * (1 - pct);

  useEffect(() => {
    const el = ringRef.current;
    if (el) {
      el.style.strokeDashoffset = String(circumference);
      requestAnimationFrame(() => {
        el.style.transition = "stroke-dashoffset 2s ease-out";
        el.style.strokeDashoffset = String(offset);
      });
    }
  }, [circumference, offset]);

  const ratingColor = rating === "Excellent" ? "text-emerald-700" : rating === "Good" ? "text-cyan-700" : "text-amber-700";
  const ratingBg = rating === "Excellent" ? "bg-emerald-50 border-emerald-200" : rating === "Good" ? "bg-cyan-50 border-cyan-200" : "bg-amber-50 border-amber-200";

  return (
    <div className="bg-white rounded-2xl border border-[#E8ECF2] p-6 mt-3 text-center shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      {/* Ring */}
      <div className="w-[110px] h-[110px] mx-auto mb-4 relative">
        <svg viewBox="0 0 120 120" className="w-full h-full" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="60" cy="60" r="50" fill="none" stroke="#F0F2F5" strokeWidth="7" />
          <circle ref={ringRef} cx="60" cy="60" r="50" fill="none" stroke="#002B5C" strokeWidth="7"
            strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference} />
        </svg>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="text-2xl font-extrabold text-[#002B5C]">{score}</div>
          <div className="text-[9px] font-medium text-[#8B95A9] uppercase tracking-wider">SIMAH</div>
        </div>
      </div>
      <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${ratingBg} ${ratingColor}`}>
        {rating} Credit Score
      </div>
    </div>
  );
}
