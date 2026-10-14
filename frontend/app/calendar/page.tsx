"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

type Item = {
  id: number;
  grant_code: string;
  grant_name: string;
  title: string;
  due_date: string;
  uc_format: string;
  status: string;
};

export default function CalendarPage() {
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    api<Item[]>("/calendar").then(setItems);
  }, []);

  return (
    <Shell>
      <h1 className="serif text-3xl">Reporting calendar</h1>
      <p className="text-sm text-[#5c675f] mt-1">UC due dates in each donor&apos;s format.</p>
      <div className="panel mt-6 overflow-x-auto">
        <table className="data w-full text-sm">
          <thead>
            <tr>
              <th>Due</th>
              <th>Grant</th>
              <th>Report</th>
              <th>Format</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.due_date}</td>
                <td>
                  {item.grant_code}
                  <div className="text-[#5c675f]">{item.grant_name}</div>
                </td>
                <td>{item.title}</td>
                <td>{item.uc_format}</td>
                <td>
                  <span className="chip bg-[#e4efe8] text-[#1f5c45]">{item.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
