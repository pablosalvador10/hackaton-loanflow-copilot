/** Contract summary card — shows contract details before signing. */

import type { ContractSummary } from "@/types";
import { FileText } from "lucide-react";

interface Props {
  data?: Record<string, unknown>;
}

export function ContractSummaryCard({ data }: Props) {
  const contract = data as unknown as ContractSummary | undefined;
  if (!contract) return null;

  const rows = [
    { label: "Contract Type", value: contract.contract_type },
    { label: "Purchase Price", value: `SAR ${contract.purchase_price?.toLocaleString()}` },
    { label: "Bank Profit", value: `SAR ${contract.bank_profit?.toLocaleString()}` },
    { label: "Total Sale Price", value: `SAR ${contract.total_sale_price?.toLocaleString()}`, highlight: true },
    { label: "Installments", value: contract.installments },
    { label: "Insurance", value: contract.insurance },
  ];

  return (
    <div className="bg-white rounded-2xl border border-[#E8ECF2] p-5 mt-3 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-[#F0F4FA] flex items-center justify-center">
          <FileText className="w-3.5 h-3.5 text-[#002B5C]" />
        </div>
        <span className="text-xs font-semibold text-[#002B5C]">{contract.contract_type} Summary</span>
      </div>
      {rows.map(r => (
        <div key={r.label} className="flex justify-between py-2.5 text-[13px] border-b border-[#F0F2F5] last:border-0">
          <span className="text-[#8B95A9]">{r.label}</span>
          <span className={r.highlight ? "font-bold text-sm text-[#002B5C]" : "font-medium text-[#1A2038]"}>
            {r.value}
          </span>
        </div>
      ))}
    </div>
  );
}
