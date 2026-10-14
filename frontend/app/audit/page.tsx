"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

type Row = { id: number; at: string; actor: string; action: string; entity: string; detail: Record<string, unknown> };

export default function AuditPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Row[]>("/audit")
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <Shell>
      <h1 className="serif text-3xl">Audit log</h1>
      <p className="text-sm text-[#5c675f] mt-1">Every upload, mapping change, budget change and publish.</p>
      {error && <p className="mt-4 text-[#9b2c2c]">{error}</p>}
      <div className="panel mt-6 overflow-x-auto">
        <table className="data w-full text-sm">
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.at}</td>
                <td>{r.actor}</td>
                <td>{r.action}</td>
                <td>{r.entity}</td>
                <td className="text-xs">{JSON.stringify(r.detail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
