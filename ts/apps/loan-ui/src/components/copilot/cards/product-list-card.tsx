/** Product list card — shows available loan products with selection. */

import { useCopilot } from "@/hooks/use-copilot";
import type { LoanProduct } from "@/types";
import { useState } from "react";

interface Props {
  data?: Record<string, unknown>;
}

export function ProductListCard({ data }: Props) {
  const { selectProduct } = useCopilot();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const products = (data as unknown as { products: LoanProduct[] })?.products || [];

  if (!products.length) return null;

  const handleSelect = (product: LoanProduct, idx: number) => {
    if (selectedIdx !== null) return;
    setSelectedIdx(idx);
    setTimeout(() => selectProduct(product), 400);
  };

  return (
    <div className="mt-3">
      <div className="flex flex-col gap-2.5">
        {products.map((p, i) => (
          <button key={p.product_id} onClick={() => handleSelect(p, i)}
            disabled={selectedIdx !== null}
            className={`text-left bg-white rounded-[14px] border-[1.5px] p-4 transition-all ${
              selectedIdx === i
                ? "border-[#002B5C] bg-[#F0F4FA] shadow-[0_0_0_3px_rgba(0,43,92,0.08)]"
                : selectedIdx !== null
                  ? "border-[#E2E6ED] opacity-50 cursor-default"
                  : "border-[#E2E6ED] hover:border-[#002B5C] hover:shadow-md hover:-translate-y-px cursor-pointer"
            }`}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-bold text-[#1A2038] flex items-center gap-2">
                {p.icon} {p.name}
              </div>
              {p.badge && (
                <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                  p.badge === "Recommended" ? "bg-[#E8F8F2] text-[#007A54]" : "bg-[#E8F0FE] text-[#002B5C]"
                }`}>{p.badge}</span>
              )}
            </div>
            <div className="text-xs text-[#6B7690] leading-snug mb-2.5">{p.description}</div>
            <div className="flex gap-4">
              <span className="text-[11px] text-[#5A6577]">Up to <strong className="text-[#002B5C]">SAR {(p.max_amount / 1000).toFixed(0)}K</strong></span>
              <span className="text-[11px] text-[#5A6577]">Tenure: <strong className="text-[#002B5C]">{p.max_tenure_months / 12} years</strong></span>
              <span className="text-[11px] text-[#5A6577]">From <strong className="text-[#002B5C]">{p.min_rate}%</strong> APR</span>
            </div>
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-3 px-3.5 py-2.5 rounded-[10px] text-xs font-semibold"
        style={{ background: "#E8F8F2", border: "1px solid #B8E5D5", color: "#007A54" }}>
        ☕ All products are certified Sharia-compliant by an independent Sharia board
      </div>
    </div>
  );
}
