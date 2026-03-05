/** Identity verified card — shows customer profile details. */

import type { CustomerProfile } from "@/types";
import { UserCheck } from "lucide-react";

interface Props {
  data?: Record<string, unknown>;
}

export function IdentityCard({ data }: Props) {
  const profile = data as unknown as CustomerProfile | undefined;
  if (!profile) return null;

  const rows = [
    { label: "Full Name", value: profile.full_name },
    { label: "National ID", value: profile.national_id },
    { label: "Employer", value: profile.employer },
    { label: "Monthly Salary", value: `SAR ${profile.monthly_salary?.toLocaleString()}` },
  ];

  return (
    <div className="bg-white rounded-2xl border border-[#E8ECF2] p-5 mt-3 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
          <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
        </div>
        <span className="text-xs font-semibold text-emerald-700">Identity Verified</span>
      </div>
      {rows.map(r => (
        <div key={r.label} className="flex justify-between py-2.5 text-[13px] border-b border-[#F0F2F5] last:border-0">
          <span className="text-[#8B95A9]">{r.label}</span>
          <span className="font-medium text-[#1A2038]">{r.value}</span>
        </div>
      ))}
    </div>
  );
}
