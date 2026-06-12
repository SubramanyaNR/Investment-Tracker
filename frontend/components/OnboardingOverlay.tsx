"use client";

interface Props {
  isVisible: boolean;
  onAddFirstAsset: () => void;
}

export default function OnboardingOverlay({ isVisible, onAddFirstAsset }: Props) {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-6">
      <div 
        className="max-w-md w-full rounded-2xl p-8 text-center space-y-6 relative overflow-hidden"
        style={{
          background: "var(--bg-elevated)",
          border: "1px solid var(--border-default)",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)"
        }}
      >
        {/* Background glow effect */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-amber-500/10 blur-[80px] rounded-full" />
        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-violet-500/10 blur-[80px] rounded-full" />

        <div className="space-y-3 relative z-10">
          <div className="mx-auto w-16 h-16 bg-amber-400/10 rounded-2xl flex items-center justify-center border border-amber-400/20 shadow-lg shadow-amber-900/20 mb-4">
            <svg className="w-8 h-8 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            Welcome to WealthSignal
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Your command center for personal wealth. Track your net worth across crypto, mutual funds, and fixed income in one unified view.
          </p>
        </div>

        <div className="pt-4 relative z-10">
          <button
            onClick={onAddFirstAsset}
            className="w-full btn-primary py-4 text-base font-bold shadow-xl shadow-amber-900/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            Add Your First Investment
          </button>
          <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.2em]" style={{ color: "var(--text-muted)" }}>
            Get started in seconds
          </p>
        </div>
      </div>
    </div>
  );
}
