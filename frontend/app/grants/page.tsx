"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, currentUser } from "@/lib/api";

type Grant = {
  code: string;
  name: string;
  donor_name: string;
  uc_format: string;
  approved_amount_inr: string;
  start_date: string;
  end_date: string | null;
  campus_pool: string;
  central_pool: string;
  primary_location: string;
  programme_lead: string | null;
};

export default function GrantsPage() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [finance, setFinance] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [importMessage, setImportMessage] = useState("");

  function load() {
    api<Grant[]>("/grants").then(setGrants);
  }

  useEffect(() => {
    setFinance(currentUser()?.role === "finance");
    load();
  }, []);

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const body = Object.fromEntries(form.entries());
    setError("");
    try {
      await api("/grants", { method: "POST", body: JSON.stringify(body) });
      setOpen(false);
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function onImport(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    setImportMessage("");
    setError("");
    try {
      const result = await api<{ created: number }>("/grants/import", { method: "POST", body: data });
      setImportMessage(`Imported ${result.created} grants.`);
      form.reset();
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Grant import failed");
    }
  }

  return (
    <Shell>
      <div className="flex justify-between items-end">
        <div>
          <h1 className="serif text-3xl">Grant master</h1>
          <p className="text-sm text-[#5c675f] mt-1">Approved amount, dates, pools and locations.</p>
        </div>
        {finance && (
          <button className="bg-[#1f5c45] text-white px-4 py-2 text-sm" onClick={() => setOpen(!open)}>
            Add grant
          </button>
        )}
      </div>

      {open && (
        <form onSubmit={onCreate} className="panel mt-6 p-5 grid grid-cols-2 gap-3 text-sm">
          {["code", "name", "donor_name", "uc_format", "approved_amount", "campus_pool", "central_pool", "primary_location"].map(
            (field) => (
              <label key={field} className="block">
                {field.replace("_", " ")}
                <input name={field} required={field !== "campus_pool"} className="mt-1 w-full border border-[#d7ccba] px-2 py-1.5" />
                {field === "campus_pool" && <span className="mt-1 block text-xs text-[#5c675f]">Leave blank if this grant is not in a campus pool.</span>}
              </label>
            )
          )}
          <label>
            start date
            <input name="start_date" type="date" required className="mt-1 w-full border border-[#d7ccba] px-2 py-1.5" />
          </label>
          <label>
            end date
            <input name="end_date" type="date" className="mt-1 w-full border border-[#d7ccba] px-2 py-1.5" />
          </label>
          {error && <p className="col-span-2 text-[#9b2c2c]">{error}</p>}
          <button className="col-span-2 bg-[#1c2a22] text-white py-2">Save</button>
        </form>
      )}

      {finance && (
        <section className="panel mt-6 p-5">
          <h2 className="font-medium">Import Grant Master</h2>
          <p className="mt-1 text-sm text-[#5c675f]">Upload a CSV or Excel workbook. Grant codes in the file must be unique and not already in Grant Master.</p>
          <form onSubmit={onImport} className="mt-3 flex flex-wrap items-end gap-3">
            <input name="file" type="file" accept=".csv,.xlsx" required className="text-sm" />
            <button className="bg-[#1f5c45] px-4 py-2 text-sm text-white">Import grants</button>
          </form>
          {importMessage && <p className="mt-3 text-sm text-[#1f5c45]">{importMessage}</p>}
          {error && <p className="mt-3 text-sm text-[#9b2c2c]">{error}</p>}
          <div className="mt-4 border-t border-[#e7dfd2] pt-3 text-sm">
            <span className="mr-3 text-[#5c675f]">Grant Master demo:</span>
            <a className="mr-3 underline" href="/templates/grant-master-demo.xlsx" download>Excel</a>
            <a className="underline" href="/templates/grant-master-demo.csv" download>CSV</a>
          </div>
        </section>
      )}

      <div className="panel mt-6 overflow-x-auto">
        <table className="data w-full text-sm">
          <thead>
            <tr>
              <th>Code</th>
              <th>Donor</th>
              <th>Approved</th>
              <th>Period</th>
              <th>Pools</th>
              <th>Lead</th>
            </tr>
          </thead>
          <tbody>
            {grants.map((g) => (
              <tr key={g.code}>
                <td>
                  <Link href={`/grants/${g.code}`} className="text-[#1f5c45] font-medium underline">
                    {g.code}
                  </Link>
                  <div className="text-[#5c675f]">{g.name}</div>
                </td>
                <td>
                  {g.donor_name}
                  <div className="text-[#5c675f]">{g.uc_format}</div>
                </td>
                <td className="num">{g.approved_amount_inr}</td>
                <td>
                  {g.start_date}
                  <div className="text-[#5c675f]">{g.end_date || "No end date"}</div>
                </td>
                <td>
                  {g.campus_pool}
                  <div className="text-[#5c675f]">{g.central_pool}</div>
                </td>
                <td>{g.programme_lead || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
