/** Copilot message — renders AI/user messages with inline cards and quick replies. */

import type { CopilotMessage as CopilotMessageType } from "@/types";
import { useCopilot } from "@/hooks/use-copilot";
import { NafathCard } from "./cards/nafath-card";
import { IdentityCard } from "./cards/identity-card";
import { ProductListCard } from "./cards/product-list-card";
import { AmountSliderCard } from "./cards/amount-slider-card";
import { CreditCheckCard } from "./cards/credit-check-card";
import { CreditScoreCard } from "./cards/credit-score-card";
import { OfferCard } from "./cards/offer-card";
import { ContractSummaryCard } from "./cards/contract-summary-card";
import { useState } from "react";

interface Props {
  message: CopilotMessageType;
}

const cardComponents: Record<string, React.FC<{ data?: Record<string, unknown> }>> = {
  "nafath-verify": NafathCard,
  "identity-card": IdentityCard,
  "product-list": ProductListCard,
  "amount-slider": AmountSliderCard,
  "credit-check": CreditCheckCard,
  "credit-score": CreditScoreCard,
  "offer-card": OfferCard,
  "contract-summary": ContractSummaryCard,
};

export function CopilotMessage({ message }: Props) {
  const { handleQuickReply } = useCopilot();
  const [repliedIdx, setRepliedIdx] = useState<number | null>(null);
  const isUser = message.role === "user";

  const CardComponent = message.card ? cardComponents[message.card] : null;

  const onReply = (text: string, idx: number) => {
    if (repliedIdx !== null) return;
    setRepliedIdx(idx);
    handleQuickReply(text);
  };

  return (
    <div className={`flex gap-3 animate-slide-in-up ${isUser ? "justify-end" : "justify-start"}`}
      style={{ animationFillMode: "forwards" }}>
      {/* AI avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center mt-0.5"
          style={{ background: "linear-gradient(135deg, #002B5C, #00A3B4)" }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
          </svg>
        </div>
      )}

      <div className={isUser ? "max-w-[80%]" : "max-w-[85%] flex-1"}>
        {/* Bubble */}
        <div className={`rounded-[18px] px-[18px] py-3.5 text-sm leading-relaxed transition-shadow ${
          isUser
            ? "rounded-br-[6px] text-white ml-auto"
            : "bg-white border border-[#E8EBF0] rounded-bl-[6px] text-[#1A2038] shadow-[0_2px_8px_rgba(0,0,0,0.05)]"
        }`}
          style={isUser ? { background: "linear-gradient(135deg, #002B5C 0%, #004080 100%)" } : undefined}
          dangerouslySetInnerHTML={{ __html: message.text }}
        />

        {/* Card */}
        {CardComponent && <CardComponent data={message.data} />}

        {/* Quick replies */}
        {message.quickReplies && message.quickReplies.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {message.quickReplies.map((r, i) => (
              <button key={i} onClick={() => onReply(r, i)}
                disabled={repliedIdx !== null}
                className={`px-[16px] py-2 rounded-full text-[13px] font-semibold transition-all duration-150 border-[1.5px] ${
                  repliedIdx === i
                    ? "bg-[#002B5C] text-white border-[#002B5C]"
                    : repliedIdx !== null
                      ? "bg-[#F7F9FC] border-[#E2E6ED] text-[#002B5C] opacity-40 cursor-default"
                      : "bg-[#F7F9FC] border-[#E2E6ED] text-[#002B5C] hover:bg-[#002B5C] hover:text-white hover:border-[#002B5C] hover:-translate-y-px cursor-pointer"
                }`}>
                {r}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center mt-0.5 bg-[#DDE2EA] text-[#5A6577] text-sm font-bold">
          MS
        </div>
      )}
    </div>
  );
}
