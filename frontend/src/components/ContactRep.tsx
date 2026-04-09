/**
 * ContactRep — contact-your-representative flow.
 *
 * Pattern adapted from democracy.io (EFF, MIT License):
 *   github.com/EFForg/democracy.io
 *
 * Flow:
 *   1. User enters their address
 *   2. We look up their US representatives via the Google Civic API
 *      (or US Congress API as fallback)
 *   3. A pre-filled message is generated based on the bill's classification
 *   4. User customizes the message before sending
 *   5. Sends via representative contact form or email
 *
 * For non-US jurisdictions, shows a manual contact prompt with guidance.
 */
"use client";
import { useState } from "react";
import type { BillSummary } from "../pages/index";

interface ContactRepProps {
  bill: BillSummary;
}

interface Representative {
  name: string;
  title: string;
  party: string;
  contact_url: string | null;
  email: string | null;
  phone: string | null;
}

interface LookupState {
  status: "idle" | "loading" | "found" | "not-found" | "error";
  reps: Representative[];
  error: string | null;
}

const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : "http://localhost:8000";

function generateDefaultMessage(bill: BillSummary): string {
  const stance =
    bill.welfare_impact === "HELPS_ANIMALS"
      ? `I am writing to urge your SUPPORT for ${bill.title}.`
      : bill.welfare_impact === "HARMS_ANIMALS"
      ? `I am writing to urge you to OPPOSE ${bill.title}.`
      : `I am writing regarding ${bill.title} and its impact on animal welfare.`;

  return [
    `Dear Representative,`,
    ``,
    stance,
    ``,
    bill.summary ?? "",
    ``,
    `This legislation directly affects animal welfare in our community. ` +
      `I urge you to carefully consider the welfare implications for the ` +
      `animals affected by this bill.`,
    ``,
    `Thank you for your service and your attention to this important matter.`,
    ``,
    `Sincerely,`,
    `[Your name]`,
  ].join("\n");
}

export function ContactRep({ bill }: ContactRepProps) {
  const isUS = bill.jurisdiction.startsWith("us");

  const [address, setAddress] = useState("");
  const [lookup, setLookup] = useState<LookupState>({
    status: "idle",
    reps: [],
    error: null,
  });
  const [selectedRep, setSelectedRep] = useState<Representative | null>(null);
  const [message, setMessage] = useState(() => generateDefaultMessage(bill));
  const [sendStatus, setSendStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [sendError, setSendError] = useState<string | null>(null);

  async function lookupReps() {
    if (!address.trim()) return;
    setLookup({ status: "loading", reps: [], error: null });

    try {
      const res = await fetch(
        `${API_BASE}/representatives?address=${encodeURIComponent(address)}&jurisdiction=${encodeURIComponent(bill.jurisdiction)}`
      );
      if (!res.ok) {
        throw new Error(`Lookup failed (${res.status})`);
      }
      const reps: Representative[] = await res.json();
      if (reps.length === 0) {
        setLookup({ status: "not-found", reps: [], error: null });
      } else {
        setLookup({ status: "found", reps, error: null });
        setSelectedRep(reps[0]);
      }
    } catch (err) {
      const error = err instanceof Error ? err.message : "Lookup failed";
      setLookup({ status: "error", reps: [], error });
    }
  }

  async function sendMessage() {
    if (!selectedRep || !message.trim()) return;
    setSendStatus("sending");
    setSendError(null);

    try {
      const res = await fetch(`${API_BASE}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bill_id: bill.bill_id,
          rep_name: selectedRep.name,
          contact_url: selectedRep.contact_url,
          email: selectedRep.email,
          message,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Send failed (${res.status})`);
      }
      setSendStatus("sent");
    } catch (err) {
      setSendStatus("error");
      setSendError(err instanceof Error ? err.message : "Failed to send");
    }
  }

  // Non-US jurisdictions: show manual guidance
  if (!isUS) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-gray-400">
          Automated representative lookup is currently available for US jurisdictions.
          For India and EU legislation, contact your representatives directly:
        </p>
        <ul className="text-sm text-gray-400 list-disc list-inside space-y-1">
          {bill.jurisdiction === "INDIA_CENTRAL" && (
            <>
              <li>
                Find your MP:{" "}
                <a
                  href="https://sansad.in/ls/members"
                  className="text-blue-400 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  sansad.in/ls/members
                </a>
              </li>
              <li>
                Contact MoEF&CC:{" "}
                <a
                  href="https://moef.gov.in"
                  className="text-blue-400 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  moef.gov.in
                </a>
              </li>
            </>
          )}
          {bill.jurisdiction === "EU" && (
            <>
              <li>
                Find your MEP:{" "}
                <a
                  href="https://www.europarl.europa.eu/meps/en/home"
                  className="text-blue-400 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  europarl.europa.eu
                </a>
              </li>
            </>
          )}
        </ul>
        <div className="mt-4">
          <label className="text-xs font-medium text-gray-400 block mb-1.5">
            Draft message (copy and use manually)
          </label>
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={10}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 font-mono focus:outline-none focus:border-gray-500 resize-y"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Address lookup */}
      {lookup.status !== "found" && (
        <div>
          <label className="text-xs font-medium text-gray-400 block mb-1.5">
            Enter your address to find your representatives
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="123 Main St, Springfield, CA 90210"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && lookupReps()}
              className="flex-1 bg-gray-950 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-gray-500"
            />
            <button
              onClick={lookupReps}
              disabled={lookup.status === "loading" || !address.trim()}
              className="px-4 py-1.5 rounded bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium text-white transition-colors"
            >
              {lookup.status === "loading" ? "Looking up..." : "Find reps"}
            </button>
          </div>
          {lookup.status === "not-found" && (
            <p className="text-sm text-yellow-400 mt-2">
              No representatives found for that address. Try a different format.
            </p>
          )}
          {lookup.status === "error" && (
            <p className="text-sm text-red-400 mt-2">{lookup.error}</p>
          )}
        </div>
      )}

      {/* Representative selection */}
      {lookup.status === "found" && (
        <div>
          <label className="text-xs font-medium text-gray-400 block mb-1.5">
            Select representative to contact
          </label>
          <select
            value={selectedRep?.name ?? ""}
            onChange={(e) => {
              const rep = lookup.reps.find((r) => r.name === e.target.value);
              setSelectedRep(rep ?? null);
            }}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-gray-500"
          >
            {lookup.reps.map((rep) => (
              <option key={rep.name} value={rep.name}>
                {rep.title} {rep.name}
                {rep.party ? ` (${rep.party})` : ""}
              </option>
            ))}
          </select>
          <button
            onClick={() => setLookup({ status: "idle", reps: [], error: null })}
            className="text-xs text-gray-500 hover:text-gray-300 mt-1"
          >
            Change address
          </button>
        </div>
      )}

      {/* Message editor */}
      <div>
        <label className="text-xs font-medium text-gray-400 block mb-1.5">
          Message — review and customize before sending
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={12}
          className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 font-mono focus:outline-none focus:border-gray-500 resize-y"
        />
      </div>

      {/* Send controls */}
      {lookup.status === "found" && selectedRep && (
        <div className="flex items-center gap-3">
          <button
            onClick={sendMessage}
            disabled={sendStatus === "sending" || sendStatus === "sent"}
            className="px-4 py-2 rounded bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium text-white transition-colors"
          >
            {sendStatus === "sending"
              ? "Sending..."
              : sendStatus === "sent"
              ? "Sent"
              : `Contact ${selectedRep.name}`}
          </button>
          {sendStatus === "sent" && (
            <p className="text-sm text-green-400">
              Message sent successfully.
            </p>
          )}
          {sendStatus === "error" && (
            <p className="text-sm text-red-400">{sendError}</p>
          )}
        </div>
      )}

      {/* Fallback manual contact link */}
      {selectedRep?.contact_url && (
        <p className="text-xs text-gray-500">
          Or contact directly via{" "}
          <a
            href={selectedRep.contact_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:underline"
          >
            official contact form
          </a>
        </p>
      )}
    </div>
  );
}
