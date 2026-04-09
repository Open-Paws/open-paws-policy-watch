/**
 * BillCard — compact summary card for a single bill.
 * Links to the full bill detail page.
 */
import Link from "next/link";
import type { BillSummary } from "../pages/index";

interface BillCardProps {
  bill: BillSummary;
}

const IMPACT_BADGE: Record<string, string> = {
  HELPS_ANIMALS: "bg-green-900 text-green-300",
  HARMS_ANIMALS: "bg-red-900 text-red-300",
  MIXED: "bg-yellow-900 text-yellow-300",
  UNRELATED: "bg-gray-800 text-gray-400",
  PENDING_CLASSIFICATION: "bg-gray-800 text-gray-500",
};

const URGENCY_BADGE: Record<string, string> = {
  IMMEDIATE: "bg-red-900 text-red-200",
  HIGH: "bg-orange-900 text-orange-200",
  MEDIUM: "bg-yellow-900 text-yellow-200",
  MONITOR: "bg-gray-800 text-gray-400",
};

export function BillCard({ bill }: BillCardProps) {
  const impactStyle =
    IMPACT_BADGE[bill.welfare_impact] ?? IMPACT_BADGE["PENDING_CLASSIFICATION"];
  const urgencyStyle = URGENCY_BADGE[bill.urgency] ?? URGENCY_BADGE["MONITOR"];

  return (
    <Link href={`/bill/${encodeURIComponent(bill.bill_id)}`}>
      <div className="block rounded-lg border border-gray-800 bg-gray-900 hover:border-gray-600 transition-colors px-4 py-3 cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white truncate">{bill.title}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {bill.jurisdiction}
              {bill.committee ? ` · ${bill.committee}` : ""}
              {bill.sponsor_name ? ` · ${bill.sponsor_name}` : ""}
            </p>
            {bill.summary && (
              <p className="text-xs text-gray-400 mt-1.5 line-clamp-2">
                {bill.summary}
              </p>
            )}
          </div>
          <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${impactStyle}`}
            >
              {bill.welfare_impact.replace(/_/g, " ")}
            </span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${urgencyStyle}`}
            >
              {bill.urgency}
            </span>
            <span className="text-xs text-gray-600">{bill.urgency_score}/100</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
