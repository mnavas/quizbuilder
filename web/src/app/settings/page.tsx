"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearAuthCookies } from "@/lib/api";

const LS_BASE_URL_KEY = "qb_base_url";

export default function SettingsPage() {
  const router = useRouter();
  const [baseUrl, setBaseUrl] = useState("");
  const [draft, setDraft] = useState("");
  const [saved, setSaved] = useState(false);

  function handleLogout() {
    clearAuthCookies();
    router.push("/login");
  }

  useEffect(() => {
    const stored = localStorage.getItem(LS_BASE_URL_KEY) || window.location.origin;
    setBaseUrl(stored);
    setDraft(stored);
  }, []);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const clean = draft.trim().replace(/\/$/, "");
    setBaseUrl(clean);
    localStorage.setItem(LS_BASE_URL_KEY, clean);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  function handleReset() {
    const origin = window.location.origin;
    setDraft(origin);
    setBaseUrl(origin);
    localStorage.setItem(LS_BASE_URL_KEY, origin);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-8">Instance configuration saved in your browser.</p>

      <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-6">

        {/* Base URL */}
        <div>
          <h2 className="text-sm font-semibold text-gray-800 mb-1">Public base URL</h2>
          <p className="text-xs text-gray-500 mb-3">
            The URL where takers reach your Quizbee instance. Used to build shareable links and QR codes
            on the Tests page. Defaults to the current browser origin.
          </p>
          <form onSubmit={handleSave} className="flex gap-2">
            <input
              type="url"
              value={draft}
              onChange={(e) => { setDraft(e.target.value); setSaved(false); }}
              placeholder="https://quizbee.yourdomain.com"
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-amber-300"
            />
            <button type="submit" className="btn-primary text-sm shrink-0">
              {saved ? "✓ Saved" : "Save"}
            </button>
          </form>
          <button
            onClick={handleReset}
            className="mt-2 text-xs text-gray-400 hover:text-gray-600"
          >
            Reset to current origin ({typeof window !== "undefined" ? window.location.origin : ""})
          </button>
        </div>

        {/* Join URL info */}
        <div className="border-t border-gray-100 pt-4">
          <h2 className="text-sm font-semibold text-gray-800 mb-1">Taker join page</h2>
          <p className="text-xs text-gray-500 mb-2">
            Write this URL on the board. Takers visit it and enter their test code.
          </p>
          <p className="text-sm font-mono bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-amber-700 select-all">
            {baseUrl}/join
          </p>
        </div>

        {/* Change password */}
        <div className="border-t border-gray-100 pt-4">
          <h2 className="text-sm font-semibold text-gray-800 mb-1">Password</h2>
          <p className="text-xs text-gray-500 mb-3">Update your account password.</p>
          <Link href="/change-password" className="btn-ghost text-sm">
            Change password →
          </Link>
        </div>

        {/* Sign out */}
        <div className="border-t border-gray-100 pt-4">
          <h2 className="text-sm font-semibold text-gray-800 mb-1">Session</h2>
          <p className="text-xs text-gray-500 mb-3">Sign out of this browser.</p>
          <button
            onClick={handleLogout}
            className="text-sm px-4 py-2 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition"
          >
            Sign out
          </button>
        </div>

        {/* About */}
        <div className="border-t border-gray-100 pt-4">
          <h2 className="text-sm font-semibold text-gray-800 mb-1">About</h2>
          <p className="text-xs text-gray-500 mb-1">Quizbee — self-hosted quiz platform.</p>
          <a
            href="https://mnavas.github.io/quizbee"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-amber-600 hover:underline"
          >
            mnavas.github.io/quizbee →
          </a>
        </div>

      </div>
    </div>
  );
}
