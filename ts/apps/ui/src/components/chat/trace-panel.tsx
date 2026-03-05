/**
 * Inline trace panel — renders the OpenTelemetry span tree
 * as a collapsible section below each bot message.
 *
 * Shows the full orchestration pipeline end-to-end:
 * latencies, span hierarchy, key attributes, and a deep-link
 * to Application Insights when configured.
 */

import { useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronRight, Activity, Clock, Copy, Check, ExternalLink } from "lucide-react";
import type { TraceDetails, TraceSpan } from "@/types";

interface TracePanelProps {
  traceDetails: TraceDetails;
}

/* ── Colour coding for latency ── */

function latencyColor(ms: number): string {
  if (ms < 500) return "text-emerald-400";
  if (ms < 2000) return "text-amber-400";
  return "text-rose-400";
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${Math.round(ms)}ms`;
}

/* ── Span badge colours by name ── */

function spanBadge(name: string): { bg: string; text: string } {
  if (name.includes("decision")) return { bg: "bg-violet-500/15", text: "text-violet-400" };
  if (name.includes("rag") || name.includes("kapa")) return { bg: "bg-blue-500/15", text: "text-blue-400" };
  if (name.includes("vector")) return { bg: "bg-cyan-500/15", text: "text-cyan-400" };
  if (name.includes("branch")) return { bg: "bg-amber-500/15", text: "text-amber-400" };
  return { bg: "bg-foreground/[0.06]", text: "text-foreground/60" };
}

/* ── Latency bar (proportional to parent) ── */

function LatencyBar({ ms, maxMs }: { ms: number; maxMs: number }) {
  const pct = maxMs > 0 ? Math.min((ms / maxMs) * 100, 100) : 0;
  return (
    <div className="h-1.5 w-20 rounded-full bg-foreground/[0.06] overflow-hidden">
      <div
        className={cn(
          "h-full rounded-full transition-all duration-500",
          ms < 500 ? "bg-emerald-500/60" : ms < 2000 ? "bg-amber-500/60" : "bg-rose-500/60"
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

/* ── Attribute pill ── */

function AttrPill({ label, value }: { label: string; value: string | number | boolean }) {
  const display = typeof value === "boolean" ? (value ? "yes" : "no") : String(value);
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-foreground/[0.04] text-foreground/40 border border-foreground/[0.06]">
      <span className="text-foreground/25">{label}:</span>
      <span>{display}</span>
    </span>
  );
}

/* ── Single span row (recursive) ── */

function SpanRow({
  span,
  depth,
  maxMs,
}: {
  span: TraceSpan;
  depth: number;
  maxMs: number;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = span.children && span.children.length > 0;
  const badge = spanBadge(span.name);
  const attrs = span.attributes ?? {};
  const attrEntries = Object.entries(attrs).filter(
    ([k]) => !["name"].includes(k)
  );

  return (
    <div className="select-none">
      {/* Span header row */}
      <div
        className={cn(
          "group flex items-center gap-2 py-1 px-1 rounded-md",
          "hover:bg-foreground/[0.03] cursor-pointer transition-colors",
        )}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {/* Expand/collapse chevron */}
        <div className="w-3.5 flex-shrink-0">
          {hasChildren ? (
            <ChevronRight
              className={cn(
                "h-3 w-3 text-foreground/25 transition-transform duration-200",
                expanded && "rotate-90"
              )}
            />
          ) : (
            <span className="block h-3 w-3" />
          )}
        </div>

        {/* Span name badge */}
        <span
          className={cn(
            "px-1.5 py-0.5 rounded text-[11px] font-mono font-medium",
            badge.bg,
            badge.text
          )}
        >
          {span.name}
        </span>

        {/* Attribute pills (inline, compact) */}
        <div className="flex gap-1 flex-wrap">
          {attrEntries.slice(0, 3).map(([k, v]) => (
            <AttrPill key={k} label={k} value={v} />
          ))}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Latency bar */}
        <LatencyBar ms={span.duration_ms} maxMs={maxMs} />

        {/* Latency value */}
        <span
          className={cn(
            "text-[11px] font-mono font-medium tabular-nums w-14 text-right",
            latencyColor(span.duration_ms)
          )}
        >
          {formatMs(span.duration_ms)}
        </span>
      </div>

      {/* Children */}
      {hasChildren && expanded && (
        <div className="border-l border-foreground/[0.06] ml-[18px]">
          {span.children.map((child, i) => (
            <SpanRow
              key={`${child.name}-${i}`}
              span={child}
              depth={depth + 1}
              maxMs={maxMs}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Copy trace ID button ── */

function CopyTraceId({ traceId }: { traceId: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(traceId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded",
        "text-[10px] font-mono text-foreground/30",
        "hover:text-foreground/50 hover:bg-foreground/[0.04]",
        "transition-colors"
      )}
      title="Copy trace ID"
    >
      {copied ? (
        <Check className="h-2.5 w-2.5 text-emerald-400" />
      ) : (
        <Copy className="h-2.5 w-2.5" />
      )}
      {traceId.slice(0, 8)}…{traceId.slice(-4)}
    </button>
  );
}

/* ── Main trace panel ── */

export function TracePanel({ traceDetails }: TracePanelProps) {
  const [open, setOpen] = useState(false);
  const rootSpan = traceDetails.spans;
  const appInsightsTraceUrlTemplate = import.meta.env.VITE_APP_INSIGHTS_TRACE_URL;
  const appInsightsTraceUrl = appInsightsTraceUrlTemplate
    ? appInsightsTraceUrlTemplate.replace("{trace_id}", traceDetails.trace_id)
    : "";

  return (
    <div className="mt-2">
      {/* Toggle button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "inline-flex items-center gap-1.5 px-2 py-1 rounded-lg",
          "text-[11px] font-medium",
          "text-foreground/25 hover:text-foreground/50",
          "hover:bg-foreground/[0.04]",
          "transition-all duration-200",
          open && "text-foreground/40 bg-foreground/[0.03]"
        )}
      >
        <Activity className="h-3 w-3" />
        <span>Trace</span>
        <span className={cn("font-mono tabular-nums", latencyColor(rootSpan.duration_ms))}>
          {formatMs(rootSpan.duration_ms)}
        </span>
        <ChevronRight
          className={cn(
            "h-3 w-3 transition-transform duration-200",
            open && "rotate-90"
          )}
        />
      </button>

      {/* Expanded content */}
      {open && (
        <div
          className={cn(
            "mt-1.5 rounded-lg overflow-hidden",
            "bg-[hsl(var(--background))]/60 backdrop-blur-sm",
            "border border-foreground/[0.06]",
            "animate-fade-in-up opacity-0"
          )}
        >
          {/* Header bar */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-foreground/[0.06]">
            <div className="flex items-center gap-2">
              <Clock className="h-3 w-3 text-foreground/20" />
              <span className="text-[10px] text-foreground/30 uppercase tracking-wider font-medium">
                Span Tree
              </span>
            </div>
            <div className="flex items-center gap-2">
              <CopyTraceId traceId={traceDetails.trace_id} />
              {appInsightsTraceUrl && (
                <a
                  href={appInsightsTraceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    "inline-flex items-center gap-1 px-1.5 py-0.5 rounded",
                    "text-[10px] font-medium text-primary/50",
                    "hover:text-primary hover:bg-primary/[0.06]",
                    "transition-colors"
                  )}
                  title="Open in App Insights"
                >
                  <ExternalLink className="h-2.5 w-2.5" />
                  App Insights
                </a>
              )}
            </div>
          </div>

          {/* Span tree */}
          <div className="px-1 py-1">
            <SpanRow
              span={rootSpan}
              depth={0}
              maxMs={rootSpan.duration_ms}
            />
          </div>
        </div>
      )}
    </div>
  );
}
