"use client";

import { FormEvent, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, currentUser } from "@/lib/api";

type Grant = {
  code: string;
  name: string;
  approved_amount_inr: string;
  budget_lines: { id: number; head: string; line_name: string; amount: string; amount_inr: string }[];
};

export default function BudgetsPage() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [code, setCode] = useState("");
  const [finance, setFinance] = useState(false);
  const [history, setHistory] = useState<{ changed_at: string; changed_by: string; note: string }[]>([]);
  const selected = grants.find((g) => g.code === code);

  function load() {
    api<Grant[]>("/grants").then((rows) => {
      setGrants(rows);
      setCode((c) => c || rows[0]?.code || "");
    });
  }

  useEffect(() => {
    setFinance(currentUser()?.role === "finance");
    load();
  }, []);

  useEffect(() => {
    if (!code) return;
    api<{ history: { changed_at: string; changed_by: string; note: string }[] }>(`/grants/${code}/budgets`).then((d) =>
      setHistory(d.history)
    );
  }, [code]);

  async function onSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selected) return;
    const rows = [...e.currentTarget.querySelectorAll<HTMLElement>("[data-line]")].map((row) => ({
      head: (row.querySelector('[name="head"]') as HTMLInputElement).value,
      line_name: (row.querySelector('[name="line_name"]') as HTMLInputElement).value,
      amount: (row.querySelector('[name="amount"]') as HTMLInputElement).value,
    }));
    await api(`/grants/${code}/budgets`, { method: "POST", body: JSON.stringify(rows) });
    load();
  }

  return (
    <Shell>
      <h1 className="serif text-3xl">Donor budgets</h1>
      <p className="text-sm text-[#5c675f] mt-1">Budget lines and heads from the grant agreement. A warning is raised if they do not equal the approved amount.</p>
      <select className="mt-4 border border-[#d7ccba] px-3 py-2 bg-white" value={code} onChange={(e) => setCode(e.target.value)}>
        {grants.map((g) => (
          <option key={g.code} value={g.code}>
            {g.code} — {g.name}
          </option>
        ))}
      </select>

      {selected && (
        <form onSubmit={onSave} className="panel mt-6 p-5">
          <div className="text-sm text-[#5c675f] mb-3">Approved {selected.approved_amount_inr}</div>
          <div className="space-y-2">
            {selected.budget_lines.map((line) => (
              <div key={line.id} data-line className="grid grid-cols-3 gap-2 text-sm">
                <input name="head" defaultValue={line.head} className="border border-[#d7ccba] px-2 py-1.5" />
                <input name="line_name" defaultValue={line.line_name} className="border border-[#d7ccba] px-2 py-1.5" />
                <input name="amount" defaultValue={line.amount} className="border border-[#d7ccba] px-2 py-1.5 num" />
              </div>
            ))}
          </div>
          {finance && <button className="mt-4 bg-[#1f5c45] text-white px-4 py-2 text-sm">Save budget</button>}
        </form>
      )}

      <h2 className="serif text-2xl mt-8">Change history</h2>
      <ul className="mt-3 text-sm space-y-1">
        {history.length === 0 && <li className="text-[#5c675f]">No replacements yet.</li>}
        {history.map((h, i) => (
          <li key={i}>
            {h.changed_at} · {h.changed_by} · {h.note}
          </li>
        ))}
      </ul>
    </Shell>
  );
}
