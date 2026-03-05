/** Nafath verification card — shows code 47 with waiting animation. */

export function NafathCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#E2E6ED] p-5 mt-3 text-center shadow-sm">
      <div className="text-[40px] font-extrabold tracking-[8px] my-3" style={{ color: "#002B5C" }}>47</div>
      <div className="text-xs text-[#6B7690]">Match this number in your Nafath app</div>
      <div className="mt-3">
        <div className="flex gap-1 justify-center py-2">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-2 h-2 rounded-full bg-[#9BA4B4] animate-pulse-dot" style={{ animationDelay: `${i * 200}ms` }} />
          ))}
        </div>
        <div className="text-[11px] text-[#9BA4B4] mt-1">Waiting for approval...</div>
      </div>
    </div>
  );
}
