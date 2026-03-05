/** Welcome screen — matches AIConversational.html design. */

const pills = [
  { icon: "💬", label: "Natural Language" },
  { icon: "☕", label: "Sharia Compliant" },
  { icon: "⚡", label: "Instant Decisions" },
  { icon: "🔒", label: "SAMA Regulated" },
];

export function WelcomeScreen({ onStart }: { onStart: () => void }) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      position: "relative", overflow: "hidden",
      background: "linear-gradient(135deg, #002B5C 0%, #004080 50%, #00A3B4 100%)",
    }}>
      {/* Decorative */}
      <div style={{
        position: "absolute", top: "-50%", right: "-30%", width: 600, height: 600,
        background: "radial-gradient(circle, rgba(0,163,180,0.2) 0%, transparent 70%)",
        borderRadius: "50%", pointerEvents: "none",
      }} />

      {/* Content */}
      <div style={{
        position: "relative", zIndex: 1, flex: 1, display: "flex",
        flexDirection: "column", justifyContent: "center", alignItems: "center",
        padding: "40px 24px", textAlign: "center",
      }}>
        {/* Logo */}
        <div style={{ marginBottom: 32, animation: "fadeInDown 0.8s ease-out" }}>
          <div style={{
            width: 80, height: 80, background: "rgba(255,255,255,0.12)",
            borderRadius: 20, display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 16px", border: "1px solid rgba(255,255,255,0.15)",
          }}>
            <svg viewBox="0 0 44 44" fill="none" width={44} height={44}>
              <path d="M22 4L38 12V28L22 36L6 28V12L22 4Z" stroke="white" strokeWidth="2" fill="none" />
              <path d="M22 4L38 12L22 20L6 12L22 4Z" fill="rgba(255,255,255,0.2)" />
              <circle cx="22" cy="20" r="6" fill="rgba(0,212,232,0.6)" stroke="white" strokeWidth="1.5" />
              <path d="M19 20L21 22L25 18" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#00C4D6", letterSpacing: 3, textTransform: "uppercase" as const }}>CREALOGIX</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#fff", letterSpacing: 3 }}>LOH</div>
          <div style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", letterSpacing: 1.5, marginTop: 4 }}>AI Lending Copilot</div>
        </div>

        {/* Hero */}
        <div style={{ marginBottom: 48, animation: "fadeInUp 0.8s ease-out 0.2s both" }}>
          <h1 style={{ fontSize: 32, fontWeight: 700, color: "#fff", lineHeight: 1.3, marginBottom: 16 }}>
            Your AI Guide to <span style={{ color: "#00D4E8" }}>Smart Lending</span>
          </h1>
          <p style={{ fontSize: 16, color: "rgba(255,255,255,0.7)", lineHeight: 1.6, maxWidth: 340, margin: "0 auto" }}>
            Chat naturally with our AI Copilot to find the perfect Sharia-compliant financing solution.
          </p>
        </div>

        {/* Pills */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, justifyContent: "center", marginBottom: 48, animation: "fadeInUp 0.8s ease-out 0.4s both" }}>
          {pills.map(p => (
            <div key={p.label} style={{
              background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 100, padding: "8px 18px", fontSize: 13, color: "rgba(255,255,255,0.9)",
              display: "flex", alignItems: "center", gap: 6,
            }}>
              <span>{p.icon}</span> {p.label}
            </div>
          ))}
        </div>

        {/* CTA */}
        <div style={{ width: "100%", maxWidth: 380, animation: "fadeInUp 0.8s ease-out 0.6s both" }}>
          <button onClick={onStart} style={{
            width: "100%", padding: "18px 32px", background: "#fff", color: "#002B5C",
            border: "none", borderRadius: 16, fontSize: 17, fontWeight: 700, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
            boxShadow: "0 4px 24px rgba(0,0,0,0.15)", fontFamily: "'Inter', sans-serif",
          }}>
            Start a Conversation
            <svg width={20} height={20} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Footer */}
      <div style={{ position: "relative", zIndex: 1, padding: 24, textAlign: "center" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.06)",
          borderRadius: 100, padding: "6px 14px", fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 10,
        }}>🏛 SAMA Licensed &amp; Regulated</div>
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", lineHeight: 1.5 }}>
          Powered by <strong style={{ color: "rgba(255,255,255,0.5)" }}>CREALOGIX</strong> LOH Platform
        </p>
      </div>
    </div>
  );
}
