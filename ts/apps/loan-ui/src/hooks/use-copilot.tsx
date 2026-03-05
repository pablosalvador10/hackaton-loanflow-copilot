/**
 * Copilot conversation engine — manages the full lending flow state.
 * Supports two modes:
 * - "mcp" (default): Direct MCP server calls with scripted flow
 * - "azure": Azure AI Agent backend via SSE streaming (loan.py)
 *
 * In Azure mode, the agent has access to all 5 MCP servers + local tools
 * and drives the conversation autonomously.
 */

import {
  createContext, useContext, useState, useCallback, useRef,
  type ReactNode,
} from "react";
import type {
  CopilotMessage, CustomerProfile, LoanProduct, CreditScore,
  LoanOffer, ContractSummary, ProgressStep,
} from "@/types";
import {
  MOCK_PROFILES, MOCK_PRODUCTS, MOCK_CREDIT_SCORES,
  mockEligibility, mockOffer, mockContract, mockDisbursement,
} from "@/lib/mock-data";
import {
  identityKyc, productCatalog, creditEligibility,
  offersPricing, contractDisbursement,
} from "@/lib/mcp-client";
import { streamConversationMessage } from "@/lib/api";

/* ── Types ── */

export type CopilotMode = "mcp" | "azure";

interface CopilotState {
  messages: CopilotMessage[];
  currentStep: number;
  progressStep: ProgressStep;
  customer: CustomerProfile | null;
  selectedProduct: LoanProduct | null;
  selectedAmount: number;
  creditScore: CreditScore | null;
  offer: LoanOffer | null;
  contract: ContractSummary | null;
  showCelebration: boolean;
  isTyping: boolean;
  mode: CopilotMode;
  startCopilot: () => void;
  handleQuickReply: (text: string) => void;
  handleSendMessage: (text: string) => void;
  selectProduct: (product: LoanProduct) => void;
  confirmAmount: (amount: number) => void;
  setShowCelebration: (v: boolean) => void;
  setMode: (m: CopilotMode) => void;
}

const STEPS: ProgressStep[] = ["identity", "needs", "product", "approval", "contract"];

const CopilotContext = createContext<CopilotState | null>(null);

/* ── Helper: try MCP, fallback to mock ── */

async function tryMcp<T>(mcpCall: () => Promise<unknown>, fallback: () => T): Promise<T> {
  try {
    return (await mcpCall()) as T;
  } catch {
    return fallback();
  }
}

/* ── Provider ── */

export function CopilotProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [customer, setCustomer] = useState<CustomerProfile | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<LoanProduct | null>(null);
  const [selectedAmount, setSelectedAmount] = useState(150000);
  const [creditScore, setCreditScore] = useState<CreditScore | null>(null);
  const [offer, setOffer] = useState<LoanOffer | null>(null);
  const [contract, setContract] = useState<ContractSummary | null>(null);
  const [showCelebration, setShowCelebration] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState<CopilotMode>("azure");
  const stepRef = useRef(0);
  const convIdRef = useRef(crypto.randomUUID());
  const historyRef = useRef<{ role: string; content: string }[]>([]);

  const addMsg = useCallback((msg: Omit<CopilotMessage, "id" | "timestamp">) => {
    const full = { ...msg, id: crypto.randomUUID(), timestamp: Date.now() };
    setMessages(prev => [...prev, full]);
    historyRef.current.push({ role: msg.role, content: msg.text });
    return full;
  }, []);

  const addAiMsg = useCallback(async (
    text: string,
    opts?: { card?: CopilotMessage["card"]; quickReplies?: string[]; triggerCelebration?: boolean; data?: Record<string, unknown>; delay?: number }
  ) => {
    setIsTyping(true);
    await new Promise(r => setTimeout(r, opts?.delay ?? 600));
    setIsTyping(false);
    return addMsg({ role: "assistant", text, ...opts });
  }, [addMsg]);

  const advanceStep = useCallback(() => {
    stepRef.current = Math.min(stepRef.current + 1, STEPS.length - 1);
    setCurrentStep(stepRef.current);
  }, []);

  /* ══════════════════════════════════════════════════════════════
   * AZURE MODE — Send message to loan.py backend, stream response
   * ══════════════════════════════════════════════════════════════ */

  const sendToAzure = useCallback(async (userText: string) => {
    setIsTyping(true);

    const botMsgId = crypto.randomUUID();
    const botMsg: CopilotMessage = {
      id: botMsgId,
      role: "assistant",
      text: "",
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, botMsg]);

    await streamConversationMessage(
      {
        conversation_id: convIdRef.current,
        message_id: crypto.randomUUID(),
        message: userText,
        history: historyRef.current.slice(0, -1), // exclude the message we just added
        application_id: null,
        document_context: null,
      },
      {
        onDelta: (text: string) => {
          setMessages(prev =>
            prev.map(m => m.id === botMsgId ? { ...m, text: m.text + text } : m)
          );
        },
        onToolStart: () => {
          // Could show a tool indicator
        },
        onDone: () => {
          setIsTyping(false);
          // Save to history
          setMessages(prev => {
            const final = prev.find(m => m.id === botMsgId);
            if (final) {
              historyRef.current.push({ role: "assistant", content: final.text });
            }
            return prev;
          });
        },
        onError: (message: string) => {
          setIsTyping(false);
          setMessages(prev =>
            prev.map(m =>
              m.id === botMsgId
                ? { ...m, text: m.text || `Sorry, something went wrong: ${message}` }
                : m
            )
          );
        },
      }
    );
  }, []);

  /* ══════════════════════════════════════════════════════════════
   * MCP MODE — Direct MCP calls with scripted flow
   * ══════════════════════════════════════════════════════════════ */

  /* ── Step 0: Welcome + Identity ── */
  const startCopilot = useCallback(async () => {
    if (mode === "azure") {
      // In Azure mode, just show a welcome message — user drives the conversation
      await addAiMsg(
        "Welcome to LOH! I'm your AI Lending Copilot. Ask me anything about financing, loan applications, or Sharia-compliant products. How can I help you today? 👋",
        { delay: 400 },
      );
      return;
    }

    await addAiMsg("Welcome to LOH! I'm your AI Lending Copilot. I'm here to help you find the perfect Sharia-compliant financing solution. 👋", { delay: 600 });
    await addAiMsg("To get started, I'll need to verify your identity. How would you like to proceed?", {
      quickReplies: ["Verify with Nafath", "Enter National ID"],
      delay: 800,
    });
  }, [addAiMsg, mode]);

  /* ── Step 1: After identity verification → needs discovery ── */
  const runIdentityFlow = useCallback(async (method: string) => {
    advanceStep();

    if (method.includes("Nafath")) {
      await addAiMsg("Connecting to Nafath... Please approve the request on your Nafath app.", { card: "nafath-verify", delay: 800 });

      await tryMcp(() => identityKyc.verifyNafath("1088000000"), () => null);
      await new Promise(r => setTimeout(r, 2000));

      const profile = await tryMcp<CustomerProfile>(
        () => identityKyc.getCustomerProfile("KYC-001") as Promise<CustomerProfile>,
        () => MOCK_PROFILES.mohammed!,
      );
      setCustomer(profile);

      await addAiMsg(`Identity verified successfully! Welcome, <strong>${profile.full_name}</strong>.`, {
        card: "identity-card", data: profile as unknown as Record<string, unknown>, delay: 800,
      });
    } else {
      const profile = MOCK_PROFILES.mohammed!;
      setCustomer(profile);
      await addAiMsg(`Identity verified via National ID. Welcome, <strong>${profile.full_name}</strong>.`, {
        card: "identity-card", data: profile as unknown as Record<string, unknown>, delay: 1200,
      });
    }

    advanceStep();
    await addAiMsg("Now, tell me — what are you looking for today? You can describe your needs in your own words, or pick one of these common options:", {
      quickReplies: ["I want to buy a car", "I need a personal loan", "Home renovation financing", "Something else"],
      delay: 800,
    });
  }, [addAiMsg, advanceStep]);

  /* ── Step 2: Product selection ── */
  const runProductFlow = useCallback(async (intent: string) => {
    advanceStep();

    const products = await tryMcp<LoanProduct[]>(
      () => productCatalog.listProducts(intent) as Promise<LoanProduct[]>,
      () => MOCK_PRODUCTS,
    );

    await addAiMsg("Great choice! Based on your needs, I've found these Sharia-compliant financing options for you:", {
      card: "product-list", data: { products } as unknown as Record<string, unknown>, delay: 800,
    });
  }, [addAiMsg, advanceStep]);

  /* ── Step 3: Amount selection ── */
  const selectProductHandler = useCallback(async (product: LoanProduct) => {
    setSelectedProduct(product);
    addMsg({ role: "user", text: `I'll go with ${product.name}` });
    advanceStep();
    await addAiMsg(`Excellent! <strong>${product.name}</strong> is a great option. How much financing do you need?`, {
      card: "amount-slider",
      data: { maxAmount: product.max_amount, minRate: product.min_rate } as unknown as Record<string, unknown>,
      delay: 800,
    });
  }, [addMsg, addAiMsg, advanceStep]);

  /* ── Step 4: Credit check + offer ── */
  const confirmAmountHandler = useCallback(async (amount: number) => {
    setSelectedAmount(amount);
    addMsg({ role: "user", text: `SAR ${amount.toLocaleString()} please` });
    advanceStep();

    const cust = customer!;
    const prod = selectedProduct!;

    await addAiMsg("Let me check your eligibility. This will only take a moment...", { card: "credit-check", delay: 600 });

    await tryMcp(() => creditEligibility.runCreditCheck(cust.customer_id), () => null);
    await new Promise(r => setTimeout(r, 4000));

    const score = await tryMcp<CreditScore>(
      () => creditEligibility.getCreditScore(cust.customer_id) as Promise<CreditScore>,
      () => MOCK_CREDIT_SCORES[cust.customer_id] ?? MOCK_CREDIT_SCORES["KYC-001"]!,
    );
    setCreditScore(score);

    await addAiMsg("Great news! Your credit assessment is complete.", {
      card: "credit-score", data: score as unknown as Record<string, unknown>, delay: 800,
    });

    const elig = await tryMcp(
      () => creditEligibility.checkEligibility(cust.customer_id, prod.type, amount),
      () => mockEligibility(cust.customer_id, prod.type, amount),
    ) as { eligible: boolean; rate?: number; approved_amount?: number; reason?: string };

    if (!elig.eligible) {
      await addAiMsg(`Unfortunately, you're not eligible for ${prod.name} at this time. ${elig.reason || ""}`, {
        quickReplies: ["Show me other options", "I understand"],
        delay: 800,
      });
      return;
    }

    const offerData = await tryMcp<LoanOffer>(
      () => offersPricing.generateOffer({
        customerId: cust.customer_id, productId: prod.product_id,
        productType: prod.type, amount: elig.approved_amount || amount,
        rate: elig.rate || prod.min_rate,
      }) as Promise<LoanOffer>,
      () => mockOffer(cust.customer_id, prod.product_id, prod.type, elig.approved_amount || amount, elig.rate || prod.min_rate),
    );
    setOffer(offerData);

    await addAiMsg("Based on your profile, here's your personalized offer:", {
      card: "offer-card", data: offerData as unknown as Record<string, unknown>, delay: 1000,
    });
    await addAiMsg("Would you like to proceed with this offer?", {
      quickReplies: ["Accept this offer", "Adjust the amount", "I need to think about it"],
      delay: 600,
    });
  }, [customer, selectedProduct, addMsg, addAiMsg, advanceStep]);

  /* ── Step 5: Contract + OTP + Disbursement ── */
  const runContractFlow = useCallback(async () => {
    advanceStep();
    const cust = customer!;
    const off = offer!;

    const contractData = await tryMcp<ContractSummary>(
      () => contractDisbursement.createContract({
        offerId: off.offer_id, customerId: cust.customer_id,
        productType: off.product_type, amount: off.amount,
        monthlyPayment: off.monthly_payment, tenureMonths: off.tenure_months,
        rate: off.annual_rate,
      }) as Promise<ContractSummary>,
      () => mockContract(off),
    );
    setContract(contractData);

    await addAiMsg(
      `Wonderful! I'm preparing your ${off.product_type} contract. This is a <strong>Sharia-compliant</strong> ${contractData.contract_type.toLowerCase()} agreement.`,
      { card: "contract-summary", data: contractData as unknown as Record<string, unknown>, delay: 800 },
    );
    await addAiMsg("I've sent a verification code to your registered mobile number. Please enter the OTP to digitally sign your contract.", {
      quickReplies: ["7 2 4 9 (Confirm OTP)"],
      delay: 1000,
    });
  }, [customer, offer, addAiMsg, advanceStep]);

  /* ── Step 6: OTP verification + disbursement ── */
  const runDisbursementFlow = useCallback(async () => {
    const cust = customer!;
    const off = offer!;
    const cont = contract!;

    await tryMcp(() => contractDisbursement.verifyOtp(cont.contract_id, "7249"), () => null);

    await addAiMsg("Contract signed successfully! Processing your disbursement via SADAD...", { delay: 800 });

    const disbursement = await tryMcp(
      () => contractDisbursement.disburseFunds(cont.contract_id, cust.customer_id, off.amount),
      () => mockDisbursement(cont.contract_id, cust.customer_id, off.amount),
    ) as { celebration: { amount: number; account_hint: string } };

    await addAiMsg(
      `All done! Your financing of <strong>SAR ${off.amount.toLocaleString()}</strong> has been disbursed. You'll receive an SMS confirmation shortly. Thank you for choosing LOH! 🎉`,
      { triggerCelebration: true, data: disbursement as unknown as Record<string, unknown>, delay: 1500 },
    );

    setTimeout(() => setShowCelebration(true), 1500);
  }, [customer, offer, contract, addAiMsg]);

  /* ── Quick reply handler ── */
  const handleQuickReply = useCallback(async (text: string) => {
    addMsg({ role: "user", text });

    if (mode === "azure") {
      await sendToAzure(text);
      return;
    }

    if (text.includes("Nafath") || text.includes("National ID")) {
      await runIdentityFlow(text);
    } else if (["I want to buy a car", "I need a personal loan", "Home renovation financing", "Something else"].includes(text)) {
      await runProductFlow(text);
    } else if (text === "Accept this offer") {
      await runContractFlow();
    } else if (text.includes("Adjust")) {
      await addAiMsg("No problem! Let's adjust your financing amount:", {
        card: "amount-slider",
        data: { maxAmount: selectedProduct?.max_amount || 500000, minRate: selectedProduct?.min_rate || 3.5 } as unknown as Record<string, unknown>,
        delay: 600,
      });
    } else if (text.includes("think about it")) {
      if (offer) {
        await tryMcp(() => offersPricing.declineOffer(offer.offer_id, "Needs more time"), () => null);
      }
      await addAiMsg("No problem at all! Your offer will be available for 7 days. Come back anytime — I'll be here. 😊", { delay: 600 });
    } else if (text.includes("7 2 4 9") || text.includes("7249")) {
      await runDisbursementFlow();
    } else if (text.includes("other options")) {
      await runProductFlow("something else");
    }
  }, [addMsg, mode, sendToAzure, runIdentityFlow, runProductFlow, runContractFlow, runDisbursementFlow, addAiMsg, selectedProduct, offer]);

  /* ── Free text handler ── */
  const handleSendMessage = useCallback(async (text: string) => {
    addMsg({ role: "user", text });

    if (mode === "azure") {
      await sendToAzure(text);
      return;
    }

    const step = stepRef.current;
    if (step <= 1) {
      await runIdentityFlow("Nafath");
    } else if (step === 2) {
      await runProductFlow(text);
    } else {
      await addAiMsg("I understand. Let me help you with that. Could you pick one of the options above?", { delay: 600 });
    }
  }, [addMsg, mode, sendToAzure, runIdentityFlow, runProductFlow, addAiMsg]);

  return (
    <CopilotContext.Provider value={{
      messages, currentStep, progressStep: STEPS[currentStep] || "identity",
      customer, selectedProduct, selectedAmount, creditScore, offer, contract,
      showCelebration, isTyping, mode,
      startCopilot, handleQuickReply, handleSendMessage,
      selectProduct: selectProductHandler, confirmAmount: confirmAmountHandler,
      setShowCelebration, setMode,
    }}>
      {children}
    </CopilotContext.Provider>
  );
}

export function useCopilot(): CopilotState {
  const ctx = useContext(CopilotContext);
  if (!ctx) throw new Error("useCopilot must be used within CopilotProvider");
  return ctx;
}
