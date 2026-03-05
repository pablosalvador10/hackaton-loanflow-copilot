/** Amount slider card — lets user pick financing amount. */

import { useState } from "react";
import { useCopilot } from "@/hooks/use-copilot";

interface Props {
  data?: Record<string, unknown>;
}

export function AmountSliderCard({ data }: Props) {
  const { confirmAmount } = useCopilot();
  const maxAmount = (data as { maxAmount?: number })?.maxAmount || 500000;
  const [amount, setAmount] = useState(150000);
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = () => {
    if (confirmed) return;
    setConfirmed(true);
    confirmAmount(amount);
  };

  return (
    <div className="mt-3 bg-white rounded-2xl border border-[#E2E6ED] p-5">
      <div className="text-xs font-semibold text-[#5A6577] uppercase tracking-wider mb-2">Financing Amount</div>
      <div className="text-[32px] font-extrabold mb-3" style={{ color: "#002B5C" }}>
        <span className="text-base text-[#9BA4B4] font-semibold">SAR </span>
        {amount.toLocaleString()}
      </div>
      <input
        type="range"
        min={50000}
        max={maxAmount}
        step={5000}
        value={amount}
        onChange={e => setAmount(Number(e.target.value))}
        disabled={confirmed}
        className="w-full h-1.5 rounded-full appearance-none bg-[#DDE2EA] outline-none
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#002B5C] [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-white
          [&::-webkit-slider-thumb]:shadow-[0_2px_8px_rgba(0,43,92,0.25)]"
      />
      <div className="flex justify-between text-[11px] text-[#6B7690] mt-1.5">
        <span>SAR 50,000</span>
        <span>SAR {maxAmount.toLocaleString()}</span>
      </div>
      <button onClick={handleConfirm} disabled={confirmed}
        className={`mt-3.5 w-full py-3 rounded-xl text-sm font-bold text-white transition-all ${
          confirmed ? "opacity-50 cursor-default" : "hover:opacity-95 hover:-translate-y-px cursor-pointer"
        }`}
        style={{ background: "linear-gradient(135deg, #002B5C 0%, #004080 100%)" }}>
        {confirmed ? "Amount Confirmed" : "Confirm Amount"}
      </button>
    </div>
  );
}
