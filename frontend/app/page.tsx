"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

type Summary = {
  run: {
    id: number;
    status: string;
    period_start: string;
    period_end: string;
    blockers: string[];
    warnings: string[];
  } | null;
  grants: {
    code: string;
    name: string;
    donor_name: string;
    approved_inr: string;
    spend_inr: string;
    balance_inr: string;
    pace: string;
    behind: boolean;
    overspent_heads: number;
  }[];
  exceptions: { grant: string | null; kind: string; message: string }[];
  unmapped_ledgers: number;
  grant_count: number;
};

function spendRatio(spend: string, approved: string): number {
  const s = parseFloat(spend.replace(/,/g, ""));
  const a = parseFloat(approved.replace(/,/g, ""));
  if (!a || isNaN(s) || isNaN(a)) return 0;
  return Math.min(s / a, 1);
}

export default function HomePage() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Summary>("/reports/summary").then(setData).catch((e) => setError(e.message));
  }, []);

  const periodLabel = data?.run
    ? `${data.run.period_start} → ${data.run.period_end}`
    : null;

  return (
    <Shell>
      {/* ── Page header ──────────────────────────────────── */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">🏠 Dashboard</h1>
        {periodLabel && (
          <p className="text-sm text-slate-500 mt-1">Period: {periodLabel}</p>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* ── Alert banners ──────────────────────────────── */}
          {data.unmapped_ledgers > 0 && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 shadow-sm">
              <span className="text-lg">⚠️</span>
              <span>
                <strong>{data.unmapped_ledgers}</strong> ledger(s) not mapped yet —{" "}
                <Link href="/mappings" className="underline font-semibold text-amber-900">
                  go to Mappings to fix
                </Link>
              </span>
            </div>
          )}
          {data.run?.status === "blocked" && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm">
              <span className="text-lg">🚫</span>
              <span>
                Latest upload has errors —{" "}
                <Link href="/uploads" className="underline font-semibold text-red-900">
                  go to Upload Data to fix
                </Link>
              </span>
            </div>
          )}

          {/* ── Stat cards ─────────────────────────────────── */}
          <div className="grid grid-cols-3 gap-4 mb-8">

            {/* Total Grants */}
            <div className="rounded-xl bg-blue-600 text-white p-5 shadow-md">
              <div className="text-2xl mb-2">🎯</div>
              <div className="text-xs font-semibold uppercase tracking-widest text-blue-200 mb-1">
                Total Grants
              </div>
              <div className="text-4xl font-bold">{data.grant_count}</div>
            </div>

            {/* Open Issues */}
            <div className={[
              "rounded-xl text-white p-5 shadow-md",
              data.exceptions.length > 0 ? "bg-orange-500" : "bg-green-600",
            ].join(" ")}>
              <div className="text-2xl mb-2">⚠️</div>
              <div className="text-xs font-semibold uppercase tracking-widest text-white/70 mb-1">
                Open Issues
              </div>
              <div className="text-4xl font-bold">{data.exceptions.length}</div>
            </div>

            {/* Data Period */}
            <div className="rounded-xl bg-slate-700 text-white p-5 shadow-md">
              <div className="text-2xl mb-2">📊</div>
              <div className="text-xs font-semibold uppercase tracking-widest text-slate-300 mb-1">
                Data Period
              </div>
              <div className="text-base font-semibold leading-snug">
                {periodLabel ?? "No data yet"}
              </div>
            </div>
          </div>

          {/* ── Grant cards grid ───────────────────────────── */}
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400 mb-3">
            All Grants
          </h2>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {data.grants.map((g) => {
              const borderColor = g.overspent_heads > 0
                ? "#dc2626"   /* red   */
                : g.behind
                ? "#d97706"   /* amber */
                : "#2563eb";  /* blue  */

              const ratio = spendRatio(g.spend_inr, g.approved_inr);
              const pctLabel = `${(ratio * 100).toFixed(0)}% used`;

              return (
                <div
                  key={g.code}
                  className="grant-card"
                  style={{ borderLeftColor: borderColor }}
                >
                  {/* Card header */}
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <div className="font-bold text-base text-slate-800 leading-tight">
                        {g.name}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">{g.donor_name}</div>
                    </div>
                    <span className={[
                      "chip shrink-0 mt-0.5",
                      g.overspent_heads > 0
                        ? "bg-red-100 text-red-700"
                        : g.behind
                        ? "bg-amber-100 text-amber-700"
                        : "bg-green-100 text-green-700",
                    ].join(" ")}>
                      {g.overspent_heads > 0 ? "Overspent" : g.pace.replace("_", " ")}
                    </span>
                  </div>

                  {/* Approved */}
                  <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-0.5">
                    Approved
                  </div>
                  <div className="num text-xl font-bold text-slate-800 mb-3">
                    ₹{g.approved_inr}
                  </div>

                  {/* Spend & Balance */}
                  <div className="flex gap-6 mb-2 text-sm">
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-slate-400">Spent</div>
                      <div className="num font-semibold text-slate-700">₹{g.spend_inr}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-slate-400">Balance</div>
                      <div className="num font-semibold text-slate-700">₹{g.balance_inr}</div>
                    </div>
                    <div className="ml-auto text-right">
                      <div className="text-[10px] uppercase tracking-widest text-slate-400">Used</div>
                      <div className="text-xs font-bold text-slate-600">{pctLabel}</div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="progress-bar-track mb-4">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${(ratio * 100).toFixed(1)}%`,
                        background: g.overspent_heads > 0 ? "#dc2626" : g.behind ? "#d97706" : "#2563eb",
                      }}
                    />
                  </div>

                  {/* Footer */}
                  <Link
                    href={`/grants/${g.code}`}
                    className="inline-flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                  >
                    View Report →
                  </Link>
                </div>
              );
            })}
          </div>
        </>
      )}
    </Shell>
  );
}
