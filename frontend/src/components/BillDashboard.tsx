/**
 * BillDashboard — filterable table of monitored bills.
 * Client component — filtering runs in browser without re-fetching.
 */
"use client";
import { useState } from "react";
import type { BillSummary } from "../pages/index";
import { BillCard } from "./BillCard";

interface BillDashboardProps {
  bills: BillSummary[];
}

const IMPACT_OPTIONS = [
  { label: "All", value: "" },
  { label: "Helps Animals", value: "HELPS_ANIMALS" },
  { label: "Harms Animals", value: "HARMS_ANIMALS" },
  { label: "Mixed", value: "MIXED" },
  { label: "Unrelated", value: "UNRELATED" },
];

const URGENCY_OPTIONS = [
  { label: "All", value: "" },
  { label: "Immediate", value: "IMMEDIATE" },
  { label: "High", value: "HIGH" },
  { label: "Medium", value: "MEDIUM" },
  { label: "Monitor", value: "MONITOR" },
];

export function BillDashboard({ bills }: BillDashboardProps) {
  const [impactFilter, setImpactFilter] = useState("");
  const [urgencyFilter, setUrgencyFilter] = useState("");
  const [search, setSearch] = useState("");

  const filtered = bills.filter((bill) => {
    if (impactFilter && bill.welfare_impact !== impactFilter) return false;
    if (urgencyFilter && bill.urgency !== urgencyFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        bill.title.toLowerCase().includes(q) ||
        bill.jurisdiction.toLowerCase().includes(q) ||
        (bill.summary ?? "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="search"
          placeholder="Search bills..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-gray-500 w-64"
        />
        <select
          value={impactFilter}
          onChange={(e) => setImpactFilter(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-gray-500"
        >
          {IMPACT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={urgencyFilter}
          onChange={(e) => setUrgencyFilter(e.target.value)}
          className="bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-gray-500"
        >
          {URGENCY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <span className="text-xs text-gray-500 ml-auto">
          {filtered.length} of {bills.length} bills
        </span>
      </div>

      {/* Bill list */}
      {filtered.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center">
          No bills match the current filters.
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((bill) => (
            <BillCard key={bill.bill_id} bill={bill} />
          ))}
        </div>
      )}
    </div>
  );
}
