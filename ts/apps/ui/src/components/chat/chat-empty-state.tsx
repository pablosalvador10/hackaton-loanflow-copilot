/**
 * Chat empty state — shown when no messages exist.
 * Centered greeting with suggested VIN prompt pills.
 */

import { cn } from "@/lib/utils";
import {
  Car,
  Search,
  ClipboardList,
  Wrench,
} from "lucide-react";

interface ChatEmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    icon: Search,
    text: "Look up VIN 1HGBH41JXMN109186",
  },
  {
    icon: Car,
    text: "Can you decode 5YJSA1E14KF123456?",
  },
  {
    icon: Wrench,
    text: "Generate a maintenance report for WBA3A5C51CF123456",
  },
  {
    icon: ClipboardList,
    text: "What vehicle is 1FTFW1ET5DFC12345?",
  },
] as const;

export function ChatEmptyState({ onPromptClick }: ChatEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 pb-8">
      {/* App icon */}
      <div
        className={cn(
          "h-16 w-16 rounded-2xl",
          "bg-primary/[0.06] border border-primary/15",
          "flex items-center justify-center",
          "mb-6",
          "animate-fade-in opacity-0"
        )}
      >
        <Car
          className="h-8 w-8 text-primary/60"
          strokeWidth={1.5}
        />
      </div>

      {/* Greeting */}
      <h1
        className={cn(
          "font-serif text-2xl sm:text-3xl md:text-[34px] font-medium",
          "text-foreground leading-tight text-center",
          "mb-2",
          "animate-fade-in-up opacity-0 [animation-delay:100ms]"
        )}
      >
        Vehicle Intelligence
      </h1>

      <p
        className={cn(
          "text-sm text-foreground/35 text-center max-w-md mb-10",
          "animate-fade-in-up opacity-0 [animation-delay:200ms]"
        )}
      >
        Paste a VIN to decode vehicle details, validate it against NHTSA, and
        generate a maintenance and lifecycle report.
      </p>

      {/* Suggested prompts — 2×2 grid */}
      <div
        className={cn(
          "grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg",
          "animate-fade-in-up opacity-0 [animation-delay:350ms]"
        )}
      >
        {SUGGESTIONS.map((suggestion) => {
          const Icon = suggestion.icon;
          return (
            <button
              key={suggestion.text}
              onClick={() => onPromptClick(suggestion.text)}
              className={cn(
                "group flex items-start gap-3",
                "px-4 py-4 rounded-xl",
                "bg-card border border-foreground/[0.06]",
                "hover:border-primary/20 hover:bg-primary/[0.02]",
                "hover:shadow-[0_2px_12px_rgba(0,0,0,0.04)]",
                "active:scale-[0.98]",
                "transition-all duration-200",
                "text-left"
              )}
            >
              <Icon
                className={cn(
                  "h-[18px] w-[18px] mt-0.5 flex-shrink-0",
                  "text-foreground/30 group-hover:text-primary/60",
                  "transition-colors"
                )}
                strokeWidth={1.5}
              />
              <span
                className={cn(
                  "text-[15px] leading-snug",
                  "text-foreground/55 group-hover:text-foreground/80",
                  "transition-colors"
                )}
              >
                {suggestion.text}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
