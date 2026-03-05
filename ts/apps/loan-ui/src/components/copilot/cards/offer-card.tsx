/** Offer card — gradient card with monthly/tenure/rate details. */

import type { LoanOffer } from "@/types";

interface Props {
  data?: Record<string, unknown>;
}

export function OfferCard({ data }: Props) {
  const offer = data as unknown as LoanOffer | undefined;
  if (!offer) return null;

  return (
    <div className="mt-3">
      <div className="rounded-[20px] p-6 text-white relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #002B5C 0%, #004080 60%, #00A3B4 100%)" }}>
        {/* Glow */}
        <div className="absolute -top-[40%] -right-[20%] w-40 h-40 rounded-full pointer-events-none"
          style={{ background: "radial-gradient(circle, rgba(0,212,232,0.15) 0%, transparent 70%)" }} />

        <div className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold tracking-wider mb-4"
          style={{ background: "rgba(255,255,255,0.15)", color: "#00D4E8" }}>
          ✨ PRE-APPROVED OFFER
        </div>

        <div className="text-[36px] font-extrabold mb-0.5">
          <span className="text-base font-semibold text-white/50">SAR </span>
          {offer.amount?.toLocaleString()}
        </div>
        <div className="text-xs text-white/45 mb-[18px]">{offer.product_type} Financing</div>

        <div className="grid grid-cols-3 gap-px rounded-xl overflow-hidden" style={{ background: "rgba(255,255,255,0.1)" }}>
          {[
            { label: "Monthly", value: offer.monthly_payment?.toLocaleString(), unit: "SAR" },
            { label: "Tenure", value: String(offer.tenure_months), unit: "months" },
            { label: "Rate", value: String(offer.annual_rate), unit: "%" },
          ].map(d => (
            <div key={d.label} className="text-center py-3 px-2" style={{ background: "rgba(0,0,0,0.15)" }}>
              <div className="text-[9px] text-white/45 uppercase tracking-wider font-semibold mb-1">{d.label}</div>
              <div className="text-base font-bold">
                {d.value} <span className="text-[10px] text-white/40 font-medium">{d.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3 px-3.5 py-2.5 rounded-[10px] text-xs font-semibold"
        style={{ background: "#E8F8F2", border: "1px solid #B8E5D5", color: "#007A54" }}>
        ☕ {offer.product_type} structure — certified by Sharia Supervisory Board
      </div>
    </div>
  );
}
