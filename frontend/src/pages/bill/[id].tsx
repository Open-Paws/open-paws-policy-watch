/**
 * Bill detail page.
 * Shows full bill information, classification reasoning, urgency breakdown,
 * and the contact-your-representative flow.
 */
import type { GetServerSideProps } from "next";
import Head from "next/head";
import Link from "next/link";
import type { BillSummary } from "../index";
import { ContactRep } from "../../components/ContactRep";

interface BillDetailProps {
  bill: BillSummary | null;
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const getServerSideProps: GetServerSideProps<BillDetailProps> = async ({
  params,
}) => {
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  if (!id) {
    return { props: { bill: null, error: "No bill ID provided" } };
  }

  try {
    const res = await fetch(`${API_BASE}/bills/${encodeURIComponent(id)}`);
    if (!res.ok) {
      return { props: { bill: null, error: `Bill not found (${res.status})` } };
    }
    const bill: BillSummary = await res.json();
    return { props: { bill, error: null } };
  } catch (err) {
    const error = err instanceof Error ? err.message : "Failed to load bill";
    return { props: { bill: null, error } };
  }
};

const IMPACT_STYLE: Record<string, string> = {
  HELPS_ANIMALS: "bg-green-900 text-green-300 border-green-700",
  HARMS_ANIMALS: "bg-red-900 text-red-300 border-red-700",
  MIXED: "bg-yellow-900 text-yellow-300 border-yellow-700",
  UNRELATED: "bg-gray-800 text-gray-400 border-gray-600",
  PENDING_CLASSIFICATION: "bg-gray-800 text-gray-400 border-gray-600",
};

const URGENCY_STYLE: Record<string, string> = {
  IMMEDIATE: "bg-red-900 text-red-200 border-red-700",
  HIGH: "bg-orange-900 text-orange-200 border-orange-700",
  MEDIUM: "bg-yellow-900 text-yellow-200 border-yellow-700",
  MONITOR: "bg-gray-800 text-gray-300 border-gray-600",
};

export default function BillDetail({ bill, error }: BillDetailProps) {
  if (error || !bill) {
    return (
      <main className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error ?? "Bill not found"}</p>
          <Link href="/" className="text-blue-400 hover:underline">
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  return (
    <>
      <Head>
        <title>{bill.title} — Open Paws Policy Watch</title>
      </Head>
      <main className="min-h-screen bg-gray-950 text-gray-100">
        <header className="border-b border-gray-800 px-6 py-4">
          <Link href="/" className="text-sm text-blue-400 hover:underline">
            ← Back to dashboard
          </Link>
        </header>

        <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
          {/* Bill header */}
          <div>
            <div className="flex flex-wrap gap-2 mb-3">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded border text-xs font-medium ${
                  IMPACT_STYLE[bill.welfare_impact] ?? IMPACT_STYLE["PENDING_CLASSIFICATION"]
                }`}
              >
                {bill.welfare_impact.replace(/_/g, " ")}
              </span>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded border text-xs font-medium ${
                  URGENCY_STYLE[bill.urgency] ?? URGENCY_STYLE["MONITOR"]
                }`}
              >
                {bill.urgency} — Score {bill.urgency_score}/100
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white">{bill.title}</h1>
            <p className="text-gray-400 mt-1 text-sm">
              {bill.jurisdiction} · {bill.status}
              {bill.committee ? ` · ${bill.committee}` : ""}
              {bill.sponsor_name ? ` · Sponsor: ${bill.sponsor_name}` : ""}
            </p>
          </div>

          {/* Summary */}
          {bill.summary && (
            <section>
              <h2 className="text-base font-semibold text-gray-300 mb-2">Summary</h2>
              <p className="text-gray-300 leading-relaxed">{bill.summary}</p>
            </section>
          )}

          {/* Classification reasoning */}
          {bill.classification_reasoning && (
            <section>
              <h2 className="text-base font-semibold text-gray-300 mb-2">
                Classification Analysis
              </h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                {bill.classification_reasoning}
              </p>
            </section>
          )}

          {/* Full text link */}
          {bill.full_text_url && (
            <p className="text-sm">
              <a
                href={bill.full_text_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 hover:underline"
              >
                View full text →
              </a>
            </p>
          )}

          {/* Contact representative flow */}
          {bill.welfare_impact !== "UNRELATED" && (
            <section className="border border-gray-800 rounded-lg p-6">
              <h2 className="text-base font-semibold text-white mb-4">
                Contact Your Representative
              </h2>
              <ContactRep bill={bill} />
            </section>
          )}
        </div>
      </main>
    </>
  );
}
