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

export default function HomePage() {
  const [data, setData] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Summary>("/reports/summary")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Shell>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="serif text-3xl">All grants</h1>
          <p className="text-sm text-[#5c675f] mt-1">
            Spend, pace and exceptions against the latest Tally run. Amounts in INR.
          </p>
        </div>
        {data?.run && (
          <div className="text-right text-sm">
            <div className="chip bg-[#1c2a22] text-white">{data.run.status}</div>
            <div className="mt-1 text-[#5c675f]">
              {data.run.period_start} → {data.run.period_end}
            </div>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-[#9b2c2c]">{error}</p>}

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="panel p-4">
              <div className="text-xs uppercase tracking-widest text-[#5c675f]">Grants</div>
              <div className="serif text-3xl mt-1">{data.grant_count}</div>
            </div>
            <div className="panel p-4">
              <div className="text-xs uppercase tracking-widest text-[#5c675f]">Unmapped ledgers</div>
              <div className="serif text-3xl mt-1">{data.unmapped_ledgers}</div>
            </div>
            <div className="panel p-4">
              <div className="text-xs uppercase tracking-widest text-[#5c675f]">Open exceptions</div>
              <div className="serif text-3xl mt-1">{data.exceptions.length}</div>
            </div>
          </div>

          <div className="panel mt-6 overflow-x-auto">
            <table className="data w-full text-sm">
              <thead>
                <tr>
                  <th>Grant</th>
                  <th>Donor</th>
                  <th>Approved</th>
                  <th>Spend</th>
                  <th>Balance</th>
                  <th>Pace</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.grants.map((g) => (
                  <tr key={g.code} className={g.overspent_heads ? "overspent" : ""}>
                    <td>
                      <div className="font-medium">{g.code}</div>
                      <div className="text-[#5c675f]">{g.name}</div>
                    </td>
                    <td>{g.donor_name}</td>
                    <td className="num">{g.approved_inr}</td>
                    <td className="num">{g.spend_inr}</td>
                    <td className="num">{g.balance_inr}</td>
                    <td>
                      <span className={`chip ${g.behind ? "bg-[#f6e6c5] text-[#9a6700]" : "bg-[#e4efe8] text-[#1f5c45]"}`}>
                        {g.pace.replace("_", " ")}
                      </span>
                    </td>
                    <td>
                      <Link className="text-[#1f5c45] underline" href={`/grants/${g.code}`}>
                        Statement
                      </Link>
                    </td>
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
