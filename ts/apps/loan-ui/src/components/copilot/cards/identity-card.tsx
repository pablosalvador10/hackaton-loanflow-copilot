/** Identity verified card — shows customer profile details. */

import type { CustomerProfile } from "@/types";

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
    <div className="bg-white rounded-2xl border border-[#E2E6ED] p-5 mt-3 shadow-sm">
      <div className="text-[13px] font-bold flex items-center gap-2 mb-3" style={{ color: "#002B5C" }}>
        ✅ Identity Verified
      </div>
      {rows.map(r => (
        <div key={r.label} className="flex justify-between py-2 text-[13px] border-b border-[#EEF1F6] last:border-0">
          <span className="text-[#6B7690]">{r.label}</span>
          <span className="font-semibold text-[#1A2038]">{r.value}</span>
        </div>
      ))}
    </div>
  );
}
