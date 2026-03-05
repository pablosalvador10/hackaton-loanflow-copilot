/** Contract summary card — shows contract details before signing. */

import type { ContractSummary } from "@/types";

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
    <div className="bg-white rounded-2xl border border-[#E2E6ED] p-5 mt-3 shadow-sm">
      <div className="text-[13px] font-bold flex items-center gap-2 mb-3" style={{ color: "#002B5C" }}>
        📄 {contract.contract_type} Summary
      </div>
      {rows.map(r => (
        <div key={r.label} className="flex justify-between py-2 text-[13px] border-b border-[#EEF1F6] last:border-0">
          <span className="text-[#6B7690]">{r.label}</span>
          <span className={r.highlight ? "font-bold text-[15px] text-[#002B5C]" : "font-semibold text-[#1A2038]"}>
            {r.value}
          </span>
        </div>
      ))}
    </div>
  );
}
