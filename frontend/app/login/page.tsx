"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("finance@org.local");
  const [password, setPassword] = useState("finance123");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      setError("Invalid email or password");
      return;
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    router.replace("/");
  }

  return (
    <div className="min-h-screen grid place-items-center px-4">
      <div className="panel w-full max-w-md p-8">
        <div className="serif text-3xl text-[#1f5c45]">Donor Utilization</div>
        <p className="mt-2 text-sm text-[#5c675f]">
          Tally exports become donor reports. Rules live in settings, not code.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block text-sm">
            Email
            <input
              className="mt-1 w-full border border-[#d7ccba] bg-white px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              type="password"
              className="mt-1 w-full border border-[#d7ccba] bg-white px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="text-sm text-[#9b2c2c]">{error}</p>}
          <button className="w-full bg-[#1f5c45] text-white py-2.5 text-sm font-medium">
            Sign in
          </button>
        </form>
        <p className="mt-6 text-xs text-[#5c675f] leading-relaxed">
          Finance: finance@org.local / finance123
          <br />
          Programme lead (EDU-PILOT only): lead@org.local / lead123
        </p>
      </div>
    </div>
  );
}
