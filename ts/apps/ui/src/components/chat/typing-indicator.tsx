/**
 * Typing indicator — three animated dots shown while the bot is thinking.
 * Uses the SAG pulseDot keyframe for smooth breathing animation.
 */

import { cn } from "@/lib/utils";

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-3 py-2.5">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className={cn(
            "h-[7px] w-[7px] rounded-full bg-foreground/25",
            "animate-pulse-dot",
            i === 1 && "animation-delay-200",
            i === 2 && "animation-delay-400"
          )}
        />
      ))}
    </div>
  );
}
