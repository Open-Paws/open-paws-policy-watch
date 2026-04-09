/**
 * Dashboard home page.
 * Shows the bill feed with filtering controls and the alert summary.
 */
import type { GetServerSideProps } from "next";
import Head from "next/head";
import { BillDashboard } from "../components/BillDashboard";
import { AlertFeed } from "../components/AlertFeed";

export interface BillSummary {
  bill_id: string;
  title: string;
  jurisdiction: string;
  status: string;
  welfare_impact: string;
  urgency: string;
  urgency_score: number;
  summary: string | null;
  full_text_url: string | null;
  sponsor_name: string | null;
  committee: string | null;
  classification_reasoning: string | null;
}

interface HomeProps {
  bills: BillSummary[];
  alerts: BillSummary[];
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const getServerSideProps: GetServerSideProps<HomeProps> = async () => {
  try {
    const [billsRes, alertsRes] = await Promise.all([
      fetch(`${API_BASE}/bills?limit=50`),
      fetch(`${API_BASE}/alerts?min_urgency=HIGH&limit=10`),
    ]);

    const bills: BillSummary[] = billsRes.ok ? await billsRes.json() : [];
    const alerts: BillSummary[] = alertsRes.ok ? await alertsRes.json() : [];

    return { props: { bills, alerts, error: null } };
  } catch (err) {
    const error = err instanceof Error ? err.message : "Failed to load bills";
    return { props: { bills: [], alerts: [], error } };
  }
};

export default function Home({ bills, alerts, error }: HomeProps) {
  return (
    <>
      <Head>
        <title>Open Paws Policy Watch</title>
        <meta
          name="description"
          content="Legislative intelligence for animal advocacy coalitions"
        />
      </Head>
      <main className="min-h-screen bg-gray-950 text-gray-100">
        <header className="border-b border-gray-800 px-6 py-4">
          <h1 className="text-xl font-semibold text-white">
            Open Paws Policy Watch
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Legislative intelligence for animal advocacy coalitions
          </p>
        </header>

        <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
          {error && (
            <div className="rounded-md bg-red-950 border border-red-800 px-4 py-3 text-red-300 text-sm">
              {error} — ensure the backend is running at {API_BASE}
            </div>
          )}

          {alerts.length > 0 && (
            <section>
              <h2 className="text-lg font-medium text-white mb-4">
                High-Urgency Alerts
              </h2>
              <AlertFeed alerts={alerts} />
            </section>
          )}

          <section>
            <h2 className="text-lg font-medium text-white mb-4">
              All Monitored Legislation
            </h2>
            <BillDashboard bills={bills} />
          </section>
        </div>
      </main>
    </>
  );
}
