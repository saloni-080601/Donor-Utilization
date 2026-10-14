"use client";

import { FormEvent, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, currentUser } from "@/lib/api";

type Payload = {
  mappings: { id: number; ledger_name: string; budget_head: string; updated_by: string; updated_at: string }[];
  history: { ledger_name: string; old_head: string | null; new_head: string; changed_by: string; changed_at: string }[];
};

export default function MappingsPage() {
  const [data, setData] = useState<Payload | null>(null);
  const [finance, setFinance] = useState(false);

  function load() {
    api<Payload>("/mappings").then(setData);
  }

  useEffect(() => {
    setFinance(currentUser()?.role === "finance");
    load();
  }, []);

  async function onSave(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    await api("/mappings", {
      method: "POST",
      body: JSON.stringify({
        ledger_name: form.get("ledger_name"),
        budget_head: form.get("budget_head"),
      }),
    });
    e.currentTarget.reset();
    load();
  }

  return (
    <Shell>
      <h1 className="serif text-3xl">Ledger mapping</h1>
      <p className="text-sm text-[#5c675f] mt-1">Which budget head each Tally ledger counts towards. Finance owns changes; every edit is kept.</p>

      {finance && (
        <form onSubmit={onSave} className="panel mt-6 p-5 grid grid-cols-3 gap-3 text-sm">
          <input name="ledger_name" required placeholder="Ledger name" className="border border-[#d7ccba] px-2 py-2" />
          <input name="budget_head" required placeholder="Budget head" className="border border-[#d7ccba] px-2 py-2" />
          <button className="bg-[#1f5c45] text-white">Save mapping</button>
        </form>
      )}

      <div className="panel mt-6 overflow-x-auto">
        <table className="data w-full text-sm">
          <thead>
            <tr>
              <th>Ledger</th>
              <th>Budget head</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {data?.mappings.map((m) => (
              <tr key={m.id}>
                <td>{m.ledger_name}</td>
                <td>{m.budget_head}</td>
                <td>
                  {m.updated_by}
                  <div className="text-[#5c675f]">{m.updated_at}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="serif text-2xl mt-8">Change history</h2>
      <div className="panel mt-3 overflow-x-auto">
        <table className="data w-full text-sm">
          <thead>
            <tr>
              <th>When</th>
              <th>Ledger</th>
              <th>From</th>
              <th>To</th>
              <th>By</th>
            </tr>
          </thead>
          <tbody>
            {data?.history.map((h, i) => (
              <tr key={i}>
                <td>{h.changed_at}</td>
                <td>{h.ledger_name}</td>
                <td>{h.old_head || "—"}</td>
                <td>{h.new_head}</td>
                <td>{h.changed_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
