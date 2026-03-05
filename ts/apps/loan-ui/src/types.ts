/** Shared TypeScript types for the LOH AI Copilot. */

/* ── Chat message ── */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

/* ── Copilot-specific message with rich cards ── */

export type CardType =
  | "nafath-verify"
  | "identity-card"
  | "product-list"
  | "amount-slider"
  | "credit-check"
  | "credit-score"
  | "offer-card"
  | "contract-summary"
  | "sharia-badge";

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  card?: CardType;
  quickReplies?: string[];
  triggerCelebration?: boolean;
  data?: Record<string, unknown>;
}

/* ── Customer profile from identity-kyc MCP ── */

export interface CustomerProfile {
  customer_id: string;
  national_id: string;
  full_name: string;
  employer: string;
  monthly_salary: number;
  employment_years: number;
  credit_rating: string;
  age: number;
  dependents: number;
  existing_obligations: number;
}

/* ── Product from product-catalog MCP ── */

export interface LoanProduct {
  product_id: string;
  name: string;
  icon: string;
  type: string;
  description: string;
  max_amount: number;
  max_tenure_months: number;
  min_rate: number;
  badge: string | null;
  sharia_structure: string;
}

/* ── Credit data from credit-eligibility MCP ── */

export interface CreditCheckStep {
  step: number;
  label: string;
  status: string;
  duration_ms: number;
}

export interface CreditScore {
  customer_id: string;
  score: number;
  rating: string;
  provider: string;
}

export interface EligibilityResult {
  eligible: boolean;
  rating: string;
  score: number;
  approved_amount?: number;
  max_amount?: number;
  rate?: number;
  capped?: boolean;
  reason?: string;
}

/* ── Offer from offers-pricing MCP ── */

export interface LoanOffer {
  offer_id: string;
  customer_id: string;
  product_id: string;
  product_type: string;
  amount: number;
  monthly_payment: number;
  tenure_months: number;
  annual_rate: number;
  total_cost: number;
  bank_profit: number;
  sharia_compliant: boolean;
  status: string;
}

/* ── Contract from contract-disbursement MCP ── */

export interface ContractSummary {
  contract_id: string;
  contract_type: string;
  description: string;
  purchase_price: number;
  bank_profit: number;
  total_sale_price: number;
  installments: string;
  insurance: string;
  status: string;
}

export interface DisbursementResult {
  disbursement_id: string;
  amount: number;
  method: string;
  account_ending: string;
  status: string;
  celebration: {
    title: string;
    message: string;
    amount: number;
    account_hint: string;
  };
}

/* ── Document upload (kept for compatibility) ── */

export interface UploadedDocument {
  documentId: string;
  fileName: string;
  documentType: string;
  base64Content: string;
  fileSize?: number;
}

/* ── Progress steps ── */

export type ProgressStep = "identity" | "needs" | "product" | "approval" | "contract";
