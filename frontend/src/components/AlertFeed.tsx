/**
 * AlertFeed — compact list of high-urgency bills requiring immediate attention.
 * Shown prominently at the top of the dashboard when alerts exist.
 */
import Link from "next/link";
import type { BillSummary } from "../pages/index";

interface AlertFeedProps {
  alerts: BillSummary[];
}

const URGENCY_COLORS: Record<string, string> = {
  IMMEDIATE: "border-red-700 bg-red-950",
  HIGH: "border-orange-700 bg-orange-950",
  MEDIUM: "border-yellow-700 bg-yellow-950",
  MONITOR: "border-gray-700 bg-gray-900",
};

const IMPACT_DOT: Record<string, string> = {
  HELPS_ANIMALS: "text-green-400",
  HARMS_ANIMALS: "text-red-400",
  MIXED: "text-yellow-400",
  UNRELATED: "text-gray-500",
  PENDING_CLASSIFICATION: "text-gray-500",
};

export function AlertFeed({ alerts }: AlertFeedProps) {
  if (alerts.length === 0) {
    return (
      <p className="text-gray-500 text-sm">No high-urgency alerts at this time.</p>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => {
        const borderStyle =
          URGENCY_COLORS[alert.urgency] ?? URGENCY_COLORS["MONITOR"];
        const dotStyle =
          IMPACT_DOT[alert.welfare_impact] ?? IMPACT_DOT["PENDING_CLASSIFICATION"];

        return (
          <Link
            key={alert.bill_id}
            href={`/bill/${encodeURIComponent(alert.bill_id)}`}
          >
            <div
              className={`flex items-start gap-3 rounded-lg border px-4 py-3 hover:opacity-80 transition-opacity cursor-pointer ${borderStyle}`}
            >
              <span className={`text-lg leading-none mt-0.5 ${dotStyle}`}>●</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white truncate">
                  {alert.title}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {alert.jurisdiction} · {alert.urgency} · Score {alert.urgency_score}/100
                  {alert.welfare_impact !== "UNRELATED"
                    ? ` · ${alert.welfare_impact.replace(/_/g, " ")}`
                    : ""}
                </p>
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
