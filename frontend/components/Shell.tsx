"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { currentUser, type User } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Summary" },
  { href: "/uploads", label: "Uploads" },
  { href: "/grants", label: "Grants" },
  { href: "/mappings", label: "Mappings" },
  { href: "/budgets", label: "Budgets" },
  { href: "/exceptions", label: "Exceptions" },
  { href: "/calendar", label: "Calendar" },
  { href: "/audit", label: "Audit", finance: true },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const u = currentUser();
    if (!u) {
      router.replace("/login");
      return;
    }
    setUser(u);
  }, [router]);

  if (!user) return <div className="p-10 text-sm text-[#5c675f]">Loading…</div>;

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 bg-[#1c2a22] text-white flex flex-col">
        <div className="px-5 py-6 border-b border-white/10">
          <div className="serif text-lg leading-tight">Donor Utilization</div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-[#9bb8a8] mt-1">
            Grant office
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {LINKS.filter((l) => !l.finance || user.role === "finance").map((link) => {
            const active = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`navlink block rounded-md px-3 py-2 text-sm ${active ? "active bg-white/10" : ""}`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-5 py-4 border-t border-white/10 text-xs text-[#9bb8a8]">
          <div className="text-white text-sm">{user.name}</div>
          <div className="capitalize">{user.role.replace("_", " ")}</div>
          <button
            className="mt-3 underline"
            onClick={() => {
              localStorage.clear();
              router.replace("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 px-8 py-8">{children}</main>
    </div>
  );
}
