/** Credit score card — animated ring with SIMAH score. */

import { useEffect, useRef } from "react";

interface Props {
  data?: Record<string, unknown>;
}

export function CreditScoreCard({ data }: Props) {
  const score = (data as { score?: number })?.score || 742;
  const rating = (data as { rating?: string })?.rating || "Excellent";
  const ringRef = useRef<SVGCircleElement>(null);

  // Animate the ring fill
  const circumference = 2 * Math.PI * 50; // r=50
  const pct = Math.min((score - 300) / 600, 1); // 300-900 range
  const offset = circumference * (1 - pct);

  useEffect(() => {
    const el = ringRef.current;
    if (el) {
      // Start fully hidden, animate to target
      el.style.strokeDashoffset = String(circumference);
      requestAnimationFrame(() => {
        el.style.transition = "stroke-dashoffset 2s ease-out";
        el.style.strokeDashoffset = String(offset);
      });
    }
  }, [circumference, offset]);

  const ratingColor = rating === "Excellent" ? "#007A54" : rating === "Good" ? "#0891B2" : "#D97706";
  const ratingBg = rating === "Excellent" ? "#E8F8F2" : rating === "Good" ? "#ECFEFF" : "#FFFBEB";
  const ratingBorder = rating === "Excellent" ? "#B8E5D5" : rating === "Good" ? "#A5F3FC" : "#FDE68A";

  return (
    <div className="rounded-2xl border p-6 mt-3 text-center"
      style={{ background: "linear-gradient(135deg, #F0F6FF 0%, #E8F0FE 100%)", borderColor: "#D0DFEF" }}>
      {/* Ring */}
      <div className="w-[120px] h-[120px] mx-auto mb-4 relative">
        <svg viewBox="0 0 120 120" className="w-full h-full" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="60" cy="60" r="50" fill="none" stroke="#DDE2EA" strokeWidth="8" />
          <circle ref={ringRef} cx="60" cy="60" r="50" fill="none" stroke="#00A3B4" strokeWidth="8"
            strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={circumference} />
        </svg>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="text-[32px] font-extrabold" style={{ color: "#002B5C" }}>{score}</div>
          <div className="text-[10px] font-semibold text-[#6B7690] uppercase tracking-wider">SIMAH</div>
        </div>
      </div>
      <div className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-bold"
        style={{ background: ratingBg, color: ratingColor, border: `1px solid ${ratingBorder}` }}>
        ⭐ {rating} Credit Score
      </div>
    </div>
  );
}
