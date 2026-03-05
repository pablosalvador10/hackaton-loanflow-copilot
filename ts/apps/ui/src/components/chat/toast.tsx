/**
 * Lightweight toast notification component.
 * Auto-dismisses after a configurable duration.
 * Uses Tailwind for styling — no external dependencies.
 */

import { useEffect, useState } from "react";

export interface ToastData {
  id: string;
  message: string;
  type?: "success" | "info" | "error";
  duration?: number;
}

interface ToastProps {
  toast: ToastData;
  onDismiss: (id: string) => void;
}

const ICON_MAP = {
  success: "✅",
  info: "ℹ️",
  error: "❌",
} as const;

const BG_MAP = {
  success:
    "bg-emerald-950/90 border-emerald-700/50 text-emerald-100",
  info: "bg-blue-950/90 border-blue-700/50 text-blue-100",
  error: "bg-red-950/90 border-red-700/50 text-red-100",
} as const;

function Toast({ toast, onDismiss }: ToastProps) {
  const [exiting, setExiting] = useState(false);
  const type = toast.type ?? "info";
  const duration = toast.duration ?? 5000;

  useEffect(() => {
    const exitTimer = setTimeout(() => setExiting(true), duration - 300);
    const removeTimer = setTimeout(() => onDismiss(toast.id), duration);
    return () => {
      clearTimeout(exitTimer);
      clearTimeout(removeTimer);
    };
  }, [toast.id, duration, onDismiss]);

  return (
    <div
      className={`
        flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg
        backdrop-blur-md transition-all duration-300
        ${BG_MAP[type]}
        ${exiting ? "opacity-0 translate-x-4" : "opacity-100 translate-x-0"}
      `}
      role="alert"
    >
      <span className="text-lg" aria-hidden>
        {ICON_MAP[type]}
      </span>
      <p className="text-sm font-medium flex-1">{toast.message}</p>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-current/50 hover:text-current transition-colors ml-2"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastData[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
