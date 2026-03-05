/** Offer card — clean card with monthly/tenure/rate details. */

import type { LoanOffer } from "@/types";
import { Shield, Star } from "lucide-react";

interface Props {
  data?: Record<string, unknown>;
}

export function OfferCard({ data }: Props) {
  const offer = data as unknown as LoanOffer | undefined;
  if (!offer) return null;

  const stats = [
    { label: "Monthly", value: offer.monthly_payment?.toLocaleString(), unit: "SAR" },
    { label: "Tenure", value: String(offer.tenure_months), unit: "months" },
    { label: "Rate", value: String(offer.annual_rate), unit: "%" },
  ];

  return (
    <div className="mt-3">
      <div className="bg-white rounded-2xl border border-[#E8ECF2] overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        {/* Header strip */}
        <div className="bg-[#002B5C] px-5 py-4">
          <div className="flex items-center gap-2 mb-3">
            <Star className="w-3.5 h-3.5 text-amber-300" />
            <span className="text-[10px] font-semibold tracking-wider text-white/70 uppercase">Pre-Approved Offer</span>
          </div>
          <div className="text-3xl font-extrabold text-white">
            <span className="text-sm font-semibold text-white/50">SAR </span>
            {offer.amount?.toLocaleString()}
          </div>
          <div className="text-xs text-white/50 mt-0.5">{offer.product_type} Financing</div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 divide-x divide-[#F0F2F5]">
          {stats.map(d => (
            <div key={d.label} className="text-center py-4 px-2">
              <div className="text-[10px] text-[#8B95A9] uppercase tracking-wider font-medium mb-1">{d.label}</div>
              <div className="text-base font-bold text-[#1A2038]">
                {d.value}
                <span className="text-[10px] text-[#8B95A9] font-normal ml-0.5">{d.unit}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded-lg text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Shield className="w-3.5 h-3.5" />
        {offer.product_type} structure — certified by Sharia Supervisory Board
      </div>
    </div>
  );
}
