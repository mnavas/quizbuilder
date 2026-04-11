"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function JoinPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = code.trim().toUpperCase().replace(/\s+/g, "");
    if (!clean) { setError("Enter your test code."); return; }
    router.push(`/take/${clean}`);
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <Image src="/icon.png" alt="Quizbee" width={36} height={36} className="rounded-lg" />
          <span className="text-2xl font-bold text-amber-500">Quizbee</span>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-1">Enter your test code</h1>
          <p className="text-sm text-gray-500 mb-6">
            Your instructor wrote a code on the board — type it below.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              ref={inputRef}
              value={code}
              onChange={(e) => { setCode(e.target.value.toUpperCase()); setError(""); }}
              placeholder="e.g. BEE4K2"
              maxLength={10}
              autoFocus
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="characters"
              spellCheck={false}
              className="w-full text-center text-3xl font-mono font-bold tracking-widest text-amber-600
                         border-2 border-gray-200 rounded-xl px-4 py-4 focus:outline-none
                         focus:border-amber-400 focus:ring-2 focus:ring-amber-100 uppercase"
            />
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="submit"
              className="w-full btn-primary text-base py-3 rounded-xl font-semibold"
            >
              Start test →
            </button>
          </form>
        </div>

        <p className="text-xs text-center text-gray-400 mt-6">
          Have a direct link? Use that instead — codes and links both work.
        </p>
      </div>
    </div>
  );
}
