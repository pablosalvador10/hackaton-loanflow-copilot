/**
 * Tool-call indicator — animated card shown while the Foundry agent is
 * executing backend MCP tools. Displays a pulsing activity bar and maps
 * raw tool names to human-readable Arabic (RTL) and English labels so the
 * user understands what is happening in real-time.
 */

import { cn } from "@/lib/utils";
import { Bot, Zap } from "lucide-react";

/* ── Tool label map ── */

/** Maps raw MCP function names to a display label. */
const TOOL_LABELS: Record<string, string> = {
  // identity_kyc
  verify_nafath: "Verifying with Nafath",
  verify_national_id: "Checking National ID",
  get_customer_profile: "Loading customer profile",
  // product_catalog
  list_loan_products: "Fetching loan products",
  get_product_details: "Retrieving product details",
  get_product_by_intent: "Matching product to your needs",
  // credit_eligibility
  run_credit_check: "Running credit check",
  get_credit_score: "Reading credit score",
  check_eligibility: "Checking eligibility",
  // offers_pricing
  generate_offer: "Generating your offer",
  calculate_monthly_payment: "Calculating monthly payment",
  adjust_offer: "Adjusting offer",
  decline_offer: "Processing decision",
  // contract_disbursement
  create_contract: "Preparing contract",
  verify_otp: "Verifying OTP",
  disburse_funds: "Processing disbursement",
  get_contract_status: "Checking contract status",
  // document tools
  validate_document_quality: "Checking document quality",
  extract_document_fields: "Extracting document data",
  assemble_application: "Assembling application",
  generate_approval_letter: "Generating approval letter",
  log_audit_event: "Logging audit event",
};

function getLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName.replace(/_/g, " ");
}

interface ToolCallIndicatorProps {
  toolNames: string[];
}

export function ToolCallIndicator({ toolNames }: ToolCallIndicatorProps) {
  const labels =
    toolNames.length > 0
      ? toolNames.map(getLabel)
      : ["Working on it…"];

  return (
    <div className="flex gap-3 animate-fade-in opacity-0">
      {/* Bot avatar */}
      <div
        className={cn(
          "flex-shrink-0 h-8 w-8 rounded-full",
          "bg-primary/[0.08] text-primary",
          "flex items-center justify-center",
          "border border-primary/15",
          "mt-0.5"
        )}
      >
        <Bot className="h-4 w-4" strokeWidth={1.5} />
      </div>

      {/* Card */}
      <div
        className={cn(
          "rounded-2xl rounded-bl-md",
          "border border-primary/[0.12] bg-primary/[0.03]",
          "px-4 py-3 flex flex-col gap-2.5"
        )}
      >
        {/* Header row */}
        <div className="flex items-center gap-2">
          <Zap className="h-3.5 w-3.5 text-primary/60 animate-pulse" strokeWidth={2} />
          <span className="text-[12px] font-medium tracking-wide text-primary/70 uppercase select-none">
            Agent is working
          </span>
        </div>

        {/* Tool labels */}
        <div className="flex flex-col gap-1.5">
          {labels.map((label, idx) => (
            <div key={idx} className="flex items-center gap-2.5">
              {/* Animated activity dot */}
              <span
                className="inline-block h-1.5 w-1.5 rounded-full bg-primary/50 animate-pulse"
                style={{ animationDelay: `${idx * 150}ms` }}
              />
              <span className="text-[13px] text-foreground/55 leading-snug">
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className="h-[2px] w-40 rounded-full bg-foreground/[0.05] overflow-hidden">
          <div
            className="h-full w-1/3 rounded-full bg-primary/40"
            style={{
              animation: "tool-bar-slide 1.4s ease-in-out infinite",
            }}
          />
        </div>
      </div>
    </div>
  );
}
