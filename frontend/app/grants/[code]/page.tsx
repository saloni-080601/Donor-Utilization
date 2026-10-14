"use client";

import { Suspense, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Shell from "@/components/Shell";
import { api, download } from "@/lib/api";

type Report = {
  grant: {
    code: string;
    name: string;
    donor_name: string;
    uc_format: string;
    approved_amount_inr: string;
    start_date: string;
    end_date: string | null;
    campus_pool: string;
    central_pool: string;
  };
  run: { id: number; status: string; start: string; end: string; blockers: string[]; warnings: string[] };
  pool_share: { campus: string | null; central: string | null };
  spend_to_date_inr: string;
  balance_inr: string;
  pace: { status: string; behind: boolean; monthly_so_far: string | null; monthly_needed: string | null };
  statement: {
    ledger: string;
    budget_head: string | null;
    direct_inr: string;
    campus_inr: string;
    central_inr: string;
    total_inr: string;
    overspent: boolean;
  }[];
  budget_vs_actual: {
    head: string;
    budget_inr: string;
    actual_inr: string;
    variance_inr: string;
    overspent: boolean;
  }[];
};

function GrantDetail() {
  const params = useParams<{ code: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Report>(`/reports/grants/${params.code}`)
      .then(setReport)
      .catch((e) => setError(e.message));
  }, [params.code]);

  return (
    <Shell>
      {error && <p className="text-[#9b2c2c]">{error}</p>}
      {report && (
        <>
          <div className="flex justify-between gap-4 items-start">
            <div>
              <div className="text-xs uppercase tracking-widest text-[#5c675f]">{report.grant.code}</div>
              <h1 className="serif text-3xl">{report.grant.name}</h1>
              <p className="text-sm text-[#5c675f] mt-1">
                {report.grant.donor_name} · {report.grant.uc_format} · {report.run.start} to {report.run.end}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                className="border border-[#1f5c45] text-[#1f5c45] px-3 py-2 text-sm"
                onClick={() => download(`/reports/grants/${params.code}/excel`, `${params.code}.xlsx`)}
              >
                Excel UC
              </button>
              <button
                className="bg-[#1f5c45] text-white px-3 py-2 text-sm"
                onClick={() => download(`/reports/grants/${params.code}/pdf`, `${params.code}.pdf`)}
              >
                PDF UC
              </button>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mt-6">
            {[
              ["Approved", report.grant.approved_amount_inr],
              ["Spend", report.spend_to_date_inr],
              ["Balance", report.balance_inr],
              ["Pace", report.pace.status.replace("_", " ")],
            ].map(([label, value]) => (
              <div key={label} className="panel p-4">
                <div className="text-xs uppercase tracking-widest text-[#5c675f]">{label}</div>
                <div className="serif text-2xl mt-1 num">{value}</div>
              </div>
            ))}
          </div>

          <p className="text-sm mt-4 text-[#5c675f]">
            Pool share — campus {report.grant.campus_pool}: {Number(report.pool_share.campus || 0).toLocaleString("en-IN", { style: "percent", maximumFractionDigits: 2 })}
            {" · "}
            central {report.grant.central_pool}: {Number(report.pool_share.central || 0).toLocaleString("en-IN", { style: "percent", maximumFractionDigits: 2 })}
            . Ledger cost = direct + (campus pool × campus share) + (central pool × central share).
          </p>

          <h2 className="serif text-2xl mt-8">Ledger statement</h2>
          <div className="panel mt-3 overflow-x-auto">
            <table className="data w-full text-sm">
              <thead>
                <tr>
                  <th>Ledger</th>
                  <th>Budget head</th>
                  <th>Direct</th>
                  <th>Campus</th>
                  <th>Central</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {report.statement.map((row) => (
                  <tr key={row.ledger} className={row.overspent ? "overspent" : ""}>
                    <td>{row.ledger}</td>
                    <td>{row.budget_head || "UNMAPPED"}</td>
                    <td className="num">{row.direct_inr}</td>
                    <td className="num">{row.campus_inr}</td>
                    <td className="num">{row.central_inr}</td>
                    <td className="num font-medium">{row.total_inr}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="serif text-2xl mt-8">Budget vs actual</h2>
          <p className="text-sm text-[#5c675f]">Lines that share a head are compared as a group.</p>
          <div className="panel mt-3 overflow-x-auto">
            <table className="data w-full text-sm">
              <thead>
                <tr>
                  <th>Head</th>
                  <th>Budget</th>
                  <th>Actual</th>
                  <th>Variance</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {report.budget_vs_actual.map((row) => (
                  <tr key={row.head} className={row.overspent ? "overspent" : ""}>
                    <td>{row.head}</td>
                    <td className="num">{row.budget_inr}</td>
                    <td className="num">{row.actual_inr}</td>
                    <td className="num">{row.variance_inr}</td>
                    <td>{row.overspent ? <span className="chip bg-[#fde8e8] text-[#9b2c2c]">Overspent</span> : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Shell>
  );
}

export default function GrantDetailPage() {
  return (
    <Suspense fallback={<Shell><p className="text-sm text-[#5c675f]">Loading…</p></Shell>}>
      <GrantDetail />
    </Suspense>
  );
}
