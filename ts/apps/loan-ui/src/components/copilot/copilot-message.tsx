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
import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot } from "lucide-react";

interface Props {
  message: CopilotMessageType;
  isLatest?: boolean;
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

export function CopilotMessage({ message, isLatest }: Props) {
  const { handleQuickReply, handleSendMessage } = useCopilot();
  const [repliedIdx, setRepliedIdx] = useState<number | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const isUser = message.role === "user";
  const cardAutoSentRef = useRef(false);

  const autoReplyRef = useRef<() => void>(() => {});
  const CardComponent = message.card ? cardComponents[message.card] : null;

  const onReply = (text: string, idx: number) => {
    if (repliedIdx !== null) return;
    setRepliedIdx(idx);
    setCountdown(null);
    handleQuickReply(text);
  };

  useEffect(() => {
    if (message.quickReplies?.length) {
      autoReplyRef.current = () => onReply(message.quickReplies![0], 0);
    }
  });

  // Auto-send card results to the AI agent so it knows to proceed
  const cardAutoSend: Record<string, { delay: number; text: string }> = {
    "nafath-verify":      { delay: 3500, text: "Nafath verification code 47 approved successfully. Please load my profile and continue." },
    "identity-card":      { delay: 2500, text: "My identity has been verified successfully. Please continue with the next step." },
    "credit-check":       { delay: 5000, text: "Credit check completed. Please share my credit score and continue." },
    "credit-score":       { delay: 3000, text: "I can see my credit score. Please continue with generating my offer." },
    "product-list":       { delay: 3500, text: "I'd like to go with the recommended Sharia-compliant product. Please continue." },
    "amount-slider":      { delay: 4000, text: "I've confirmed my financing amount. Please proceed with the credit check." },
    "offer-card":         { delay: 3500, text: "I can see the offer and I'd like to accept it. Please proceed with the contract." },
    "contract-summary":   { delay: 3500, text: "I've reviewed the contract summary. Please proceed with signing and disbursement." },
  };

  useEffect(() => {
    if (!isLatest || !message.card || cardAutoSentRef.current) return;
    const config = cardAutoSend[message.card];
    if (!config) return;
    const timer = setTimeout(() => {
      if (!cardAutoSentRef.current) {
        cardAutoSentRef.current = true;
        handleSendMessage(config.text);
      }
    }, config.delay);
    return () => clearTimeout(timer);
  }, [isLatest, message.card, handleSendMessage]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!isLatest || !message.quickReplies?.length || isUser) return;
    let count = 3;
    setCountdown(count);
    const interval = setInterval(() => {
      count--;
      setCountdown(count > 0 ? count : null);
      if (count <= 0) clearInterval(interval);
    }, 1000);
    const timer = setTimeout(() => autoReplyRef.current(), 3000);
    return () => { clearInterval(interval); clearTimeout(timer); };
  }, [isLatest]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className={`flex gap-3 animate-slide-in-up ${isUser ? "justify-end" : "justify-start"}`}
      style={{ animationFillMode: "forwards" }}>
      {/* AI avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#002B5C] flex items-center justify-center mt-0.5">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={isUser ? "max-w-[75%]" : "max-w-[80%] flex-1"}>
        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "rounded-br-md bg-[#002B5C] text-white ml-auto"
            : "bg-white border border-[#E8ECF2] rounded-bl-md text-[#1A2038] shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
        }`}>
          {isUser ? (
            <span>{message.text}</span>
          ) : (
            <div className="copilot-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.text}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Card */}
        {CardComponent && <CardComponent data={message.data} />}

        {/* Quick replies */}
        {message.quickReplies && message.quickReplies.length > 0 && (
          <div className="mt-3">
            <div className="flex flex-wrap gap-2">
              {message.quickReplies.map((r, i) => {
                const isSelected = repliedIdx === i;
                const isDisabled = repliedIdx !== null && !isSelected;
                const isPrimary = i === 0 && countdown !== null && repliedIdx === null;
                return (
                  <button
                    key={i}
                    onClick={() => onReply(r, i)}
                    disabled={repliedIdx !== null}
                    className={`px-4 py-2 rounded-xl text-[13px] font-medium transition-all duration-150 border ${
                      isSelected
                        ? "bg-[#002B5C] text-white border-[#002B5C]"
                        : isDisabled
                          ? "bg-[#F4F5F7] border-[#E8ECF2] text-[#A0A8B8] cursor-default"
                          : isPrimary
                            ? "bg-white border-[#002B5C]/30 text-[#002B5C] hover:bg-[#002B5C] hover:text-white"
                            : "bg-white border-[#E8ECF2] text-[#1A2038] hover:border-[#002B5C]/30 hover:bg-[#F8F9FC]"
                    }`}
                  >
                    {r}
                    {i === 0 && countdown !== null && repliedIdx === null && (
                      <span className="ml-1.5 text-[11px] opacity-60">({countdown}s)</span>
                    )}
                  </button>
                );
              })}
            </div>
            {countdown !== null && repliedIdx === null && (
              <div className="mt-2 h-[2px] rounded-full bg-[#F0F2F5] overflow-hidden max-w-[200px]">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-linear bg-[#002B5C]/30"
                  style={{ width: `${(countdown / 3) * 100}%` }}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
