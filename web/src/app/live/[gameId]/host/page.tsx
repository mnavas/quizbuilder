"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useParams } from "next/navigation";
import QRCode from "qrcode";
import { api } from "@/lib/api";
import RichTextViewer from "@/components/RichTextViewer";

function QrModal({ url, onClose }: { url: string; onClose: () => void }) {
  const [dataUrl, setDataUrl] = useState("");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    QRCode.toDataURL(url, { width: 280, margin: 2, color: { dark: "#111827", light: "#ffffff" } }).then(setDataUrl);
  }, [url]);
  function copy() { navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 shadow-xl max-w-xs w-full text-center" onClick={(e) => e.stopPropagation()}>
        <p className="text-sm font-semibold text-gray-700 mb-1">Scan to join</p>
        <p className="text-xs text-gray-400 mb-3">Opens the join page on players&apos; phones</p>
        {dataUrl
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={dataUrl} alt="QR code" className="mx-auto rounded-lg" />
          : <div className="w-[280px] h-[280px] mx-auto bg-gray-100 rounded-lg animate-pulse" />}
        <button onClick={copy}
          className={`mt-3 w-full text-xs py-2 rounded-lg font-medium transition ${copied ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
          {copied ? "✓ Copied!" : "Copy link"}
        </button>
        <p className="text-xs text-gray-300 mt-2 break-all font-mono leading-relaxed">{url}</p>
      </div>
    </div>
  );
}

type PlayerInLobby = { nickname: string; avatar_color: string };
type LiveQuestion = { id: string; type: string; prompt_json: any; options_json: any[] | null };
type LeaderboardEntry = {
  nickname: string; avatar_color: string; points_earned: number | null;
  is_correct: boolean | null; total_score: number; rank: number;
};
type GameState = {
  state: string; game_id: string; pin: string;
  question_index: number; question_count: number; time_limit_seconds: number;
  players?: PlayerInLobby[];
  question?: LiveQuestion;
  time_remaining_ms?: number;
  answered_count?: number;
  player_count?: number;
  correct_answer?: any;
  options_json?: any[] | null;
  top_question?: LeaderboardEntry[];
  top_cumulative?: LeaderboardEntry[];
};

const OPTION_COLORS = ["#ef4444", "#3b82f6", "#eab308", "#22c55e"];
const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

function Avatar({ color, nickname }: { color: string; nickname: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
        style={{ backgroundColor: color }}>
        {nickname[0]?.toUpperCase()}
      </span>
      <span className="text-sm font-medium text-gray-800 truncate">{nickname}</span>
    </div>
  );
}

function CountdownRing({ remaining_ms, total_ms }: { remaining_ms: number; total_ms: number }) {
  const pct = Math.max(0, remaining_ms / total_ms);
  const secs = Math.ceil(remaining_ms / 1000);
  const r = 36;
  const circumference = 2 * Math.PI * r;
  const dashoffset = circumference * (1 - pct);
  const color = secs <= 5 ? "#ef4444" : secs <= 10 ? "#f97316" : "#22c55e";
  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={r} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={dashoffset}
          style={{ transition: "stroke-dashoffset 0.5s linear, stroke 0.5s" }} />
      </svg>
      <span className="text-3xl font-bold tabular-nums" style={{ color }}>{secs}</span>
    </div>
  );
}

export default function HostPage() {
  const { gameId } = useParams() as { gameId: string };
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [advancing, setAdvancing] = useState(false);
  const [error, setError] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [showQr, setShowQr] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function poll() {
    try {
      const res = await api.get(`/live/games/${gameId}/state`);
      setGameState(res.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Connection error");
    }
  }

  useEffect(() => {
    setBaseUrl(localStorage.getItem("qb_base_url") || window.location.origin);
    poll();
    pollRef.current = setInterval(poll, 1000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [gameId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleNext() {
    setAdvancing(true);
    try {
      await api.post(`/live/games/${gameId}/next`);
      await poll();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Error");
    } finally {
      setAdvancing(false);
    }
  }

  if (!gameState) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <p className="text-white text-sm">Loading…</p>
    </div>
  );

  const { state, pin, question_index, question_count, time_limit_seconds } = gameState;

  // ── Waiting (Lobby) ────────────────────────────────────────────────────────
  if (state === "waiting") return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      <header className="flex items-center justify-between px-8 py-4 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Image src="/icon-64.png" alt="QuizBuilder" width={28} height={28} />
          <span className="font-bold text-amber-400">QuizBuilder Live</span>
        </div>
        <span className="text-sm text-gray-400">{question_count} question{question_count !== 1 ? "s" : ""}</span>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center gap-8 p-8">
        <div className="text-center">
          <p className="text-gray-400 text-sm mb-2">Players join at</p>
          <div className="flex items-center justify-center gap-3">
            <p className="text-xl font-mono font-semibold text-white">{baseUrl}/live-join</p>
            <button
              onClick={() => setShowQr(true)}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition text-white"
              title="Show QR code"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z" />
                <path strokeLinecap="round" strokeLinejoin="round"
                  d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75V16.5zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z" />
              </svg>
            </button>
          </div>
        </div>

        {showQr && <QrModal url={`${baseUrl}/live-join?pin=${pin}`} onClose={() => setShowQr(false)} />}

        <div className="bg-white/10 rounded-3xl px-16 py-10 text-center">
          <p className="text-gray-400 text-sm mb-2 tracking-widest uppercase">Game PIN</p>
          <p className="text-7xl font-black tracking-[0.2em] text-amber-400 font-mono">{pin}</p>
        </div>

        <div className="text-center">
          <p className="text-2xl font-bold">{gameState.players?.length ?? 0} player{(gameState.players?.length ?? 0) !== 1 ? "s" : ""} joined</p>
        </div>

        {(gameState.players?.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-3 justify-center max-w-2xl">
            {gameState.players!.map((p) => (
              <div key={p.nickname} className="flex items-center gap-2 bg-white/10 rounded-full px-4 py-2">
                <span className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
                  style={{ backgroundColor: p.avatar_color }}>
                  {p.nickname[0]?.toUpperCase()}
                </span>
                <span className="text-sm font-medium">{p.nickname}</span>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          onClick={handleNext}
          disabled={advancing || (gameState.players?.length ?? 0) === 0}
          className="px-10 py-4 rounded-2xl text-xl font-bold bg-amber-500 hover:bg-amber-400 text-white disabled:opacity-40 transition"
        >
          {advancing ? "Starting…" : "Start Game →"}
        </button>
      </div>
    </div>
  );

  // ── Question Active ────────────────────────────────────────────────────────
  if (state === "question_active") {
    const q = gameState.question;
    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col">
        <header className="flex items-center justify-between px-8 py-3 border-b border-white/10">
          <span className="text-sm text-gray-400">
            Question {question_index + 1} / {question_count}
          </span>
          <span className="text-sm text-gray-400">
            {gameState.answered_count ?? 0} / {gameState.player_count ?? 0} answered
          </span>
        </header>

        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-8">
          {gameState.time_remaining_ms !== undefined && (
            <CountdownRing
              remaining_ms={gameState.time_remaining_ms}
              total_ms={time_limit_seconds * 1000}
            />
          )}

          {q && (
            <div className="bg-white/10 rounded-2xl p-8 w-full max-w-3xl">
              <RichTextViewer content={q.prompt_json} className="text-2xl font-semibold text-white text-center leading-relaxed" />
            </div>
          )}

          {q?.options_json && q.options_json.length > 0 && (
            <div className="grid grid-cols-2 gap-4 w-full max-w-3xl">
              {q.options_json.map((opt: any, i: number) => (
                <div key={opt.id}
                  className="rounded-2xl p-5 flex items-center gap-3 text-white font-semibold text-lg"
                  style={{ backgroundColor: OPTION_COLORS[i % OPTION_COLORS.length] }}>
                  <span className="w-9 h-9 rounded-lg bg-black/20 flex items-center justify-center text-sm font-bold shrink-0">
                    {OPTION_LABELS[i]}
                  </span>
                  <RichTextViewer content={opt.content_json} className="text-white" />
                </div>
              ))}
            </div>
          )}

          {q?.type === "true_false" && (
            <div className="grid grid-cols-2 gap-4 w-full max-w-3xl">
              {[{ label: "True", val: "true", color: OPTION_COLORS[0] }, { label: "False", val: "false", color: OPTION_COLORS[1] }].map((o) => (
                <div key={o.val} className="rounded-2xl p-6 text-white font-bold text-2xl text-center"
                  style={{ backgroundColor: o.color }}>
                  {o.label}
                </div>
              ))}
            </div>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={handleNext}
            disabled={advancing}
            className="px-8 py-3 rounded-2xl font-bold bg-white/20 hover:bg-white/30 text-white disabled:opacity-40 transition"
          >
            {advancing ? "Closing…" : "Close Question →"}
          </button>
        </div>
      </div>
    );
  }

  // ── Question Closed (leaderboard) ──────────────────────────────────────────
  if (state === "question_closed") {
    const opts = gameState.options_json ?? [];
    const correctAns = gameState.correct_answer;
    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col">
        <header className="flex items-center justify-between px-8 py-3 border-b border-white/10">
          <span className="text-sm text-gray-400">Question {question_index + 1} / {question_count} — Results</span>
        </header>

        <div className="flex-1 flex flex-col items-center p-8 gap-6 max-w-3xl mx-auto w-full">
          {/* Correct answer highlight */}
          {opts.length > 0 && (
            <div className="w-full space-y-3">
              {opts.map((opt: any, i: number) => {
                const isCorrect = correctAns === opt.id ||
                  (typeof correctAns === "object" && correctAns?.value === opt.id);
                return (
                  <div key={opt.id}
                    className={`rounded-xl p-4 flex items-center gap-3 transition ${isCorrect ? "ring-4 ring-white/60" : "opacity-40"}`}
                    style={{ backgroundColor: OPTION_COLORS[i % OPTION_COLORS.length] }}>
                    <span className="w-8 h-8 rounded-lg bg-black/20 flex items-center justify-center text-sm font-bold shrink-0">
                      {OPTION_LABELS[i]}
                    </span>
                    <RichTextViewer content={opt.content_json} className="text-white font-semibold" />
                    {isCorrect && <span className="ml-auto text-2xl">✓</span>}
                  </div>
                );
              })}
            </div>
          )}

          {/* True/false answer */}
          {!opts.length && (correctAns === "true" || correctAns === "false" || correctAns?.value) && (
            <div className="w-full space-y-3">
              {[{ label: "True", val: "true", color: OPTION_COLORS[0] }, { label: "False", val: "false", color: OPTION_COLORS[1] }].map((o) => {
                const isCorrect = (correctAns === o.val || correctAns?.value === o.val);
                return (
                  <div key={o.val} className={`rounded-xl p-5 text-white font-bold text-xl text-center transition ${isCorrect ? "ring-4 ring-white/60" : "opacity-40"}`}
                    style={{ backgroundColor: o.color }}>
                    {o.label} {isCorrect && "✓"}
                  </div>
                );
              })}
            </div>
          )}

          {/* Top players this question */}
          {(gameState.top_question?.length ?? 0) > 0 && (
            <div className="w-full">
              <p className="text-gray-400 text-xs uppercase tracking-widest mb-3">This question</p>
              <div className="space-y-2">
                {gameState.top_question!.map((entry) => (
                  <div key={entry.nickname}
                    className={`flex items-center gap-3 rounded-xl px-4 py-3 ${entry.is_correct ? "bg-white/10" : "bg-white/5 opacity-60"}`}>
                    <span className="text-lg font-bold w-7 text-center text-gray-400">#{entry.rank}</span>
                    <Avatar color={entry.avatar_color} nickname={entry.nickname} />
                    <span className="ml-auto font-bold text-amber-400">+{entry.points_earned ?? 0}</span>
                    <span className="text-gray-400 text-sm w-20 text-right">{entry.total_score.toLocaleString()} pts</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={handleNext}
            disabled={advancing}
            className="px-10 py-4 rounded-2xl text-lg font-bold bg-amber-500 hover:bg-amber-400 text-white disabled:opacity-40 transition"
          >
            {advancing ? "Loading…" : question_index + 1 >= question_count ? "Show Final Results →" : "Next Question →"}
          </button>
        </div>
      </div>
    );
  }

  // ── Finished ───────────────────────────────────────────────────────────────
  if (state === "finished") {
    const top = gameState.top_cumulative ?? [];
    const podium = [top[1], top[0], top[2]].filter(Boolean);
    const podiumHeights = ["h-28", "h-40", "h-20"];
    const podiumPositions = [1, 0, 2];

    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col">
        <header className="flex items-center justify-between px-8 py-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <Image src="/icon-64.png" alt="QuizBuilder" width={24} height={24} />
            <span className="font-bold text-amber-400">Game Over</span>
          </div>
        </header>

        <div className="flex-1 flex flex-col items-center p-8 gap-8 max-w-2xl mx-auto w-full">
          <h1 className="text-3xl font-black">Final Leaderboard</h1>

          {/* Podium */}
          {top.length >= 1 && (
            <div className="flex items-end justify-center gap-4 w-full">
              {[top[1], top[0], top[2]].filter(Boolean).map((entry, i) => {
                const heights = ["h-28", "h-40", "h-20"];
                const medals = ["🥈", "🥇", "🥉"];
                const ranks = [2, 1, 3];
                if (!entry) return null;
                return (
                  <div key={entry.nickname} className="flex flex-col items-center gap-2 flex-1">
                    <span className="text-3xl">{medals[i]}</span>
                    <span className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg"
                      style={{ backgroundColor: entry.avatar_color }}>
                      {entry.nickname[0]?.toUpperCase()}
                    </span>
                    <span className="text-sm font-semibold text-center truncate w-full text-center">{entry.nickname}</span>
                    <span className="text-amber-400 font-bold">{entry.total_score.toLocaleString()}</span>
                    <div className={`w-full rounded-t-xl bg-white/20 ${heights[i]}`} />
                  </div>
                );
              })}
            </div>
          )}

          {/* Full list */}
          <div className="w-full space-y-2">
            {top.map((entry) => (
              <div key={entry.nickname}
                className={`flex items-center gap-3 rounded-xl px-4 py-3 ${entry.rank <= 3 ? "bg-amber-500/20 border border-amber-500/30" : "bg-white/5"}`}>
                <span className="text-lg font-bold w-7 text-center">
                  {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `#${entry.rank}`}
                </span>
                <Avatar color={entry.avatar_color} nickname={entry.nickname} />
                <span className="ml-auto font-bold text-xl text-amber-400">{entry.total_score.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
