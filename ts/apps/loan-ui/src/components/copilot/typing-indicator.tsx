/** Typing indicator — shown while the AI is thinking (before the first token arrives). */

export function TypingIndicator() {
  return (
    <div className="flex gap-3 justify-start animate-fade-in">
      <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center"
        style={{ background: "linear-gradient(135deg, #002B5C, #00A3B4)" }}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <div className="bg-white border border-[#E2E6ED] rounded-[18px] rounded-bl-[6px] px-[18px] py-3.5 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            {[0, 1, 2].map(i => (
              <div key={i}
                className="w-2 h-2 rounded-full bg-[#9BA4B4]"
                style={{
                  animation: "typingBounce 1.4s ease-in-out infinite",
                  animationDelay: `${i * 0.2}s`,
                }} />
            ))}
          </div>
          <span className="text-[11px] text-[#9BA4B4] font-medium tracking-wide">Thinking…</span>
        </div>
      </div>
    </div>
  );
}
