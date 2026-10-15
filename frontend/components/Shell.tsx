"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { currentUser, type User } from "@/lib/api";

const LINKS = [
  { href: "/",          label: "Dashboard",   emoji: "🏠" },
  { href: "/uploads",   label: "Upload Data", emoji: "📤" },
  { href: "/grants",    label: "Grants",      emoji: "🎯" },
  { href: "/mappings",  label: "Mappings",    emoji: "🔗" },
  { href: "/budgets",   label: "Budgets",     emoji: "💰" },
  { href: "/exceptions",label: "Issues",      emoji: "⚠️" },
  { href: "/calendar",  label: "Calendar",    emoji: "📅" },
  { href: "/audit",     label: "Audit Log",   emoji: "🔍", finance: true },
];

function ShellContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const u = currentUser();
    if (!u) { router.replace("/login"); return; }
    setUser(u);
  }, [router]);

  if (!user) return (
    <div className="flex items-center justify-center min-h-screen bg-[#f0f4f8]">
      <div className="text-sm text-slate-500">Loading…</div>
    </div>
  );

  const isFinance = user.role === "finance";

  return (
    <div className="min-h-screen flex bg-[#f0f4f8]">

      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="w-52 shrink-0 bg-[#1e293b] text-white flex flex-col">

        {/* Logo area */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="text-base font-bold tracking-tight">
            📋 Donor UC
          </div>
          <div className="text-[10px] uppercase tracking-widest text-slate-400 mt-0.5">
            Grant Office
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-2 py-4 space-y-0.5">
          {LINKS.filter((l) => !l.finance || isFinance).map((link) => {
            const active =
              pathname === link.href ||
              (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={[
                  "navlink flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all",
                  active
                    ? "active bg-blue-600 text-white font-semibold shadow-sm"
                    : "text-slate-300 hover:bg-white/8 hover:text-white",
                ].join(" ")}
              >
                <span className="text-base leading-none w-5 text-center">{link.emoji}</span>
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User area */}
        <div className="px-4 py-4 border-t border-white/10">
          <div className="text-sm font-semibold text-white">{user.name}</div>
          <div className="mt-1">
            <span className={[
              "inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide",
              isFinance
                ? "bg-blue-500/30 text-blue-200"
                : "bg-slate-600 text-slate-300",
            ].join(" ")}>
              {user.role.replace("_", " ")}
            </span>
          </div>
          <button
            className="mt-3 text-xs text-slate-400 hover:text-white transition-colors underline"
            onClick={() => { localStorage.clear(); router.replace("/login"); }}
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────── */}
      <main className="flex-1 min-w-0 px-8 py-8">{children}</main>
    </div>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="p-10 text-sm text-[#5c675f]">Loading...</div>}>
      <ShellContent>{children}</ShellContent>
    </Suspense>
  );
}
