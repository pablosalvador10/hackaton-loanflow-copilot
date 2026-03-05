/** Product list card — shows available loan products with selection. */

import { useCopilot } from "@/hooks/use-copilot";
import type { LoanProduct } from "@/types";
import { useState, useEffect, useRef } from "react";
import { Shield } from "lucide-react";

interface Props {
  data?: Record<string, unknown>;
}

export function ProductListCard({ data }: Props) {
  const { selectProduct } = useCopilot();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [countdown, setCountdown] = useState(3);
  const confirmedRef = useRef(false);
  const products = (data as unknown as { products: LoanProduct[] })?.products || [];

  if (!products.length) return null;

  const handleSelect = (product: LoanProduct, idx: number) => {
    if (confirmedRef.current) return;
    confirmedRef.current = true;
    setSelectedIdx(idx);
    setCountdown(0);
    setTimeout(() => selectProduct(product), 400);
  };

  // Auto-select recommended (first) product after 3s
  useEffect(() => {
    if (!products.length) return;
    let count = 3;
    const interval = setInterval(() => {
      count--;
      setCountdown(count);
      if (count <= 0) clearInterval(interval);
    }, 1000);
    const timer = setTimeout(() => {
      if (!confirmedRef.current) handleSelect(products[0], 0);
    }, 3000);
    return () => { clearInterval(interval); clearTimeout(timer); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-3">
      <div className="flex flex-col gap-2">
        {products.map((p, i) => (
          <button key={p.product_id} onClick={() => handleSelect(p, i)}
            disabled={selectedIdx !== null}
            className={`text-left bg-white rounded-xl border p-4 transition-all duration-200 ${
              selectedIdx === i
                ? "border-[#002B5C] bg-[#F8FAFF] ring-2 ring-[#002B5C]/10"
                : selectedIdx !== null
                  ? "border-[#E8ECF2] opacity-40 cursor-default"
                  : "border-[#E8ECF2] hover:border-[#002B5C]/30 hover:shadow-md cursor-pointer"
            }`}>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-semibold text-[#1A2038] flex items-center gap-2">
                {p.icon} {p.name}
              </span>
              {p.badge && (
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${
                  p.badge === "Recommended"
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-[#F0F4FA] text-[#002B5C]"
                }`}>
                  {p.badge}
                  {i === 0 && countdown > 0 && selectedIdx === null && (
                    <span className="ml-1 opacity-60">({countdown}s)</span>
                  )}
                </span>
              )}
            </div>
            <p className="text-xs text-[#6B7690] leading-snug mb-3">{p.description}</p>
            <div className="flex gap-4 text-[11px] text-[#8B95A9]">
              <span>Up to <strong className="text-[#1A2038]">SAR {(p.max_amount / 1000).toFixed(0)}K</strong></span>
              <span>Tenure: <strong className="text-[#1A2038]">{p.max_tenure_months / 12}yr</strong></span>
              <span>From <strong className="text-[#1A2038]">{p.min_rate}%</strong></span>
            </div>
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-3 px-3 py-2 rounded-lg text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <Shield className="w-3.5 h-3.5" />
        All products are certified Sharia-compliant
      </div>
    </div>
  );
}
