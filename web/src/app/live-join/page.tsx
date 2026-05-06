"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function LiveJoinInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pin, setPin] = useState("");
  const [nickname, setNickname] = useState("");
  const [step, setStep] = useState<"pin" | "nickname">("pin");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // If a PIN is pre-filled via URL (e.g. from a QR code), skip straight to nickname
  useEffect(() => {
    const prePin = searchParams.get("pin")?.replace(/\D/g, "").slice(0, 6) ?? "";
    if (prePin.length === 6) {
      setPin(prePin);
      setStep("nickname");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handlePinSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = pin.trim().replace(/\s+/g, "");
    if (clean.length !== 6 || !/^\d{6}$/.test(clean)) {
      setError("Enter the 6-digit PIN shown on the screen.");
      return;
    }
    setPin(clean);
    setError("");
    setStep("nickname");
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    const nick = nickname.trim();
    if (!nick) { setError("Enter a nickname."); return; }
    setLoading(true); setError("");
    try {
      const res = await api.post("/live/join", { pin, nickname: nick });
      const { game_id, player_id, avatar_color } = res.data;
      // Store in localStorage for reconnection
      localStorage.setItem(`live_player_${game_id}`, player_id);
      localStorage.setItem(`live_nick_${game_id}`, nick);
      localStorage.setItem(`live_color_${game_id}`, avatar_color);
      router.push(`/live/${game_id}/play?player_id=${player_id}&nickname=${encodeURIComponent(nick)}&avatar_color=${encodeURIComponent(avatar_color)}`);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Could not join. Check the PIN and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex items-center justify-center gap-2">
          <Image src="/icon-64.png" alt="QuizBuilder" width={36} height={36} />
          <span className="text-2xl font-bold text-amber-400">QuizBuilder Live</span>
        </div>

        <div className="bg-white/10 rounded-2xl p-8 text-white">
          {step === "pin" ? (
            <>
              <h1 className="text-xl font-bold text-center mb-1">Enter Game PIN</h1>
              <p className="text-gray-400 text-sm text-center mb-6">Ask your host for the 6-digit PIN.</p>
              <form onSubmit={handlePinSubmit} className="space-y-4">
                <input
                  value={pin}
                  onChange={(e) => { setPin(e.target.value.replace(/\D/g, "").slice(0, 6)); setError(""); }}
                  placeholder="000000"
                  maxLength={6}
                  autoFocus
                  autoComplete="off"
                  inputMode="numeric"
                  className="w-full text-center text-4xl font-black tracking-[0.3em] font-mono text-amber-400
                             bg-white/10 border-2 border-white/20 rounded-xl px-4 py-4
                             focus:outline-none focus:border-amber-400 placeholder-white/20"
                />
                {error && <p className="text-red-400 text-sm text-center">{error}</p>}
                <button
                  type="submit"
                  disabled={pin.length !== 6}
                  className="w-full py-3 rounded-xl font-bold text-base bg-amber-500 hover:bg-amber-400 text-white disabled:opacity-40 transition"
                >
                  Continue →
                </button>
              </form>
            </>
          ) : (
            <>
              <h1 className="text-xl font-bold text-center mb-1">Choose a Nickname</h1>
              <p className="text-gray-400 text-sm text-center mb-6">PIN: <span className="font-mono text-amber-400 font-bold tracking-widest">{pin}</span></p>
              <form onSubmit={handleJoin} className="space-y-4">
                <input
                  value={nickname}
                  onChange={(e) => { setNickname(e.target.value.slice(0, 30)); setError(""); }}
                  placeholder="Your name…"
                  maxLength={30}
                  autoFocus
                  autoComplete="off"
                  className="w-full text-center text-2xl font-bold text-white
                             bg-white/10 border-2 border-white/20 rounded-xl px-4 py-4
                             focus:outline-none focus:border-amber-400 placeholder-white/20"
                />
                {error && <p className="text-red-400 text-sm text-center">{error}</p>}
                <button
                  type="submit"
                  disabled={loading || !nickname.trim()}
                  className="w-full py-3 rounded-xl font-bold text-base bg-amber-500 hover:bg-amber-400 text-white disabled:opacity-40 transition"
                >
                  {loading ? "Joining…" : "Join Game →"}
                </button>
                <button
                  type="button"
                  onClick={() => { setStep("pin"); setError(""); }}
                  className="w-full text-sm text-gray-400 hover:text-white transition"
                >
                  ← Change PIN
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-gray-600 text-xs text-center">Have a regular test code? <a href="/join" className="text-amber-400 hover:underline">Go to /join</a></p>
      </div>
    </div>
  );
}

export default function LiveJoinPage() {
  return (
    <Suspense>
      <LiveJoinInner />
    </Suspense>
  );
}
