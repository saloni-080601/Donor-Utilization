"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";

type Item = { grant: string | null; kind: string; message: string };

export default function ExceptionsPage() {
  const [items, setItems] = useState<Item[]>([]);

  useEffect(() => {
    api<Item[]>("/reports/exceptions").then(setItems);
  }, []);

  return (
    <Shell>
      <h1 className="serif text-3xl">Exceptions</h1>
      <p className="text-sm text-[#5c675f] mt-1">Unmapped ledgers, reconciling gaps, pace flags and overspent heads.</p>
      <div className="mt-6 space-y-3">
        {items.length === 0 && <div className="panel p-5 text-sm">No exceptions on the latest run.</div>}
        {items.map((item, i) => (
          <div key={i} className="panel p-4 flex gap-4 text-sm">
            <span
              className={`chip ${
                item.kind === "block" || item.kind === "overspend"
                  ? "bg-[#fde8e8] text-[#9b2c2c]"
                  : "bg-[#f6e6c5] text-[#9a6700]"
              }`}
            >
              {item.kind}
            </span>
            <div>
              {item.grant && <div className="font-medium">{item.grant}</div>}
              <div>{item.message}</div>
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}
