/** Amount slider card — lets user pick financing amount. */

import { useState, useEffect, useRef } from "react";
import { useCopilot } from "@/hooks/use-copilot";

interface Props {
  data?: Record<string, unknown>;
}

export function AmountSliderCard({ data }: Props) {
  const { confirmAmount } = useCopilot();
  const maxAmount = (data as { maxAmount?: number })?.maxAmount || 500000;
  const [amount, setAmount] = useState(150000);
  const [confirmed, setConfirmed] = useState(false);
  const [countdown, setCountdown] = useState(3);
  const confirmedRef = useRef(false);

  const handleConfirm = (amt?: number) => {
    if (confirmedRef.current) return;
    confirmedRef.current = true;
    setConfirmed(true);
    confirmAmount(amt ?? amount);
  };

  const amountRef = useRef(amount);
  useEffect(() => { amountRef.current = amount; }, [amount]);

  useEffect(() => {
    let count = 3;
    const interval = setInterval(() => {
      count--;
      setCountdown(count);
      if (count <= 0) clearInterval(interval);
    }, 1000);
    const timer = setTimeout(() => handleConfirm(amountRef.current), 3000);
    return () => { clearInterval(interval); clearTimeout(timer); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="mt-3 bg-white rounded-2xl border border-[#E8ECF2] p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="text-[11px] font-medium text-[#8B95A9] uppercase tracking-wider mb-2">Financing Amount</div>
      <div className="text-[28px] font-extrabold text-[#002B5C] mb-4">
        <span className="text-sm text-[#8B95A9] font-medium">SAR </span>
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
        className="w-full h-1.5 rounded-full appearance-none bg-[#E8ECF2] outline-none
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#002B5C] [&::-webkit-slider-thumb]:cursor-pointer
          [&::-webkit-slider-thumb]:border-[3px] [&::-webkit-slider-thumb]:border-white
          [&::-webkit-slider-thumb]:shadow-md"
      />
      <div className="flex justify-between text-[10px] text-[#8B95A9] mt-1.5">
        <span>SAR 50,000</span>
        <span>SAR {maxAmount.toLocaleString()}</span>
      </div>
      <button onClick={() => handleConfirm()} disabled={confirmed}
        className={`mt-4 w-full py-3 rounded-xl text-sm font-semibold text-white transition-all duration-200 ${
          confirmed
            ? "bg-emerald-600 cursor-default"
            : "bg-[#002B5C] hover:bg-[#003A75] hover:-translate-y-px hover:shadow-md active:scale-[0.98]"
        }`}>
        {confirmed ? "Amount Confirmed \u2713" : `Confirm Amount${countdown > 0 ? ` (${countdown}s)` : ""}`}
      </button>
      {!confirmed && (
        <div className="mt-2 h-[2px] rounded-full bg-[#F0F2F5] overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000 ease-linear bg-[#002B5C]/20"
            style={{ width: `${(countdown / 3) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}
