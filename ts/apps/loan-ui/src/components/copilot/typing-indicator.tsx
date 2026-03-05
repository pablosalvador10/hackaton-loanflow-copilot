/** Typing indicator — shown while the AI is thinking. */

import { Bot } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex gap-3 justify-start animate-fade-in">
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-[#002B5C] flex items-center justify-center">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-white border border-[#E8ECF2] rounded-2xl rounded-bl-md px-4 py-3 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-2.5">
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <div key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#002B5C]/30"
                style={{
                  animation: "typingBounce 1.4s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }} />
            ))}
          </div>
          <span className="text-[11px] text-[#8B95A9] font-medium">Thinking...</span>
        </div>
      </div>
    </div>
  );
}
