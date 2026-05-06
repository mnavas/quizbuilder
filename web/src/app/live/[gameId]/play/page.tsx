"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import RichTextViewer from "@/components/RichTextViewer";

type LiveQuestion = { id: string; type: string; prompt_json: any; options_json: any[] | null };
type LeaderboardEntry = {
  nickname: string; avatar_color: string; points_earned: number | null;
  is_correct: boolean | null; total_score: number; rank: number;
};
type GameState = {
  state: string; game_id: string; pin: string;
  question_index: number; question_count: number; time_limit_seconds: number;
  player_count?: number;
  question?: LiveQuestion;
  time_remaining_ms?: number;
  answered_count?: number;
  correct_answer?: any;
  options_json?: any[] | null;
  top_question?: LeaderboardEntry[];
  top_cumulative?: LeaderboardEntry[];
};
type PlayerResult = {
  answered: boolean; is_correct: boolean; points_earned: number;
  time_ms?: number; total_score: number; rank: number;
};

const OPTION_COLORS = ["#ef4444", "#3b82f6", "#eab308", "#22c55e"];
const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

export default function PlayPage() {
  const { gameId } = useParams() as { gameId: string };
  const searchParams = useSearchParams();

  const [playerId, setPlayerId] = useState<string | null>(null);
  const [nickname, setNickname] = useState<string | null>(null);
  const [avatarColor, setAvatarColor] = useState("#f59e0b");
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [answered, setAnswered] = useState<string | null>(null); // question_id of answered question
  const [playerResult, setPlayerResult] = useState<PlayerResult | null>(null);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prevStateRef = useRef<string>("");
  const prevQIdxRef = useRef<number>(-1);

  // Restore from searchParams or localStorage
  useEffect(() => {
    const pid = searchParams.get("player_id") || localStorage.getItem(`live_player_${gameId}`);
    const nick = searchParams.get("nickname") || localStorage.getItem(`live_nick_${gameId}`);
    const color = searchParams.get("avatar_color") || localStorage.getItem(`live_color_${gameId}`) || "#f59e0b";
    if (pid) { setPlayerId(pid); setNickname(nick); setAvatarColor(color); }
  }, [gameId, searchParams]);

  async function poll() {
    if (!playerId) return;
    try {
      const res = await api.get(`/live/games/${gameId}/state`);
      const gs: GameState = res.data;
      setGameState(gs);

      // When question closes, fetch player result
      const qId = gs.question_index >= 0 && gs.state === "question_closed"
        ? (gs as any).question?.id ?? null
        : null;

      if (
        gs.state === "question_closed" &&
        (prevStateRef.current !== "question_closed" || prevQIdxRef.current !== gs.question_index)
      ) {
        // Need the question id — fetch from state's top_question or use a dedicated call
        // We'll fetch via player result endpoint using the question_index
        fetchPlayerResult(gs);
      }

      prevStateRef.current = gs.state;
      prevQIdxRef.current = gs.question_index;
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Connection error");
    }
  }

  async function fetchPlayerResult(gs: GameState) {
    if (!playerId) return;
    // We need the question ID — it's in the top_question list or we stored it from question_active
    const qId = storedQuestionIdRef.current;
    if (!qId) return;
    try {
      const res = await api.get(
        `/live/games/${gameId}/player/${playerId}/result?question_id=${qId}`
      );
      setPlayerResult(res.data);
    } catch { /* ignore */ }
  }

  const storedQuestionIdRef = useRef<string>("");

  // When state is question_active, store the current question id
  useEffect(() => {
    if (gameState?.state === "question_active" && gameState.question?.id) {
      storedQuestionIdRef.current = gameState.question.id;
      setPlayerResult(null);
    }
    // Reset answered flag when a new question becomes active
    if (gameState?.state === "question_active") {
      setAnswered(null);
    }
  }, [gameState?.state, gameState?.question_index]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!playerId) return;
    poll();
    pollRef.current = setInterval(poll, 1000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [playerId, gameId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function submitAnswer(value: any) {
    if (!playerId || !gameState || gameState.state !== "question_active") return;
    const qId = gameState.question?.id;
    if (!qId || answered === qId) return;
    setAnswered(qId);
    try {
      await api.post(`/live/games/${gameId}/answer`, { player_id: playerId, value });
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Answer not saved");
      setAnswered(null);
    }
  }

  // ── No player yet — should not happen (redirected from join page) ──────────
  if (!playerId) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center space-y-4 p-8">
        <p className="text-white text-sm">Player session not found.</p>
        <a href="/live-join" className="text-amber-400 underline text-sm">Go back to join page</a>
      </div>
    </div>
  );

  if (!gameState) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <p className="text-white text-sm">Connecting…</p>
    </div>
  );

  const { state, pin, question_index, question_count, time_limit_seconds } = gameState;

  // ── Waiting ────────────────────────────────────────────────────────────────
  if (state === "waiting") return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center gap-8 p-6">
      <Image src="/icon-64.png" alt="QuizBuilder" width={48} height={48} />
      <div className="text-center">
        <div className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold mx-auto mb-3"
          style={{ backgroundColor: avatarColor }}>
          {(nickname || "?")[0]?.toUpperCase()}
        </div>
        <p className="text-white text-xl font-bold">{nickname}</p>
        <p className="text-gray-400 text-sm mt-1">You&apos;re in! Waiting for the host to start…</p>
      </div>
      <div className="text-center">
        <p className="text-gray-500 text-sm">PIN: <span className="text-amber-400 font-mono font-bold tracking-widest">{pin}</span></p>
        <p className="text-gray-500 text-sm mt-1">{gameState.player_count ?? "..."} players joined</p>
      </div>
      <div className="flex gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: "0ms" }} />
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: "150ms" }} />
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );

  // ── Question Active ────────────────────────────────────────────────────────
  if (state === "question_active") {
    const q = gameState.question;
    const hasAnswered = answered === q?.id;
    const pct = Math.max(0, (gameState.time_remaining_ms ?? 0) / (time_limit_seconds * 1000));
    const secs = Math.ceil((gameState.time_remaining_ms ?? 0) / 1000);

    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col">
        {/* Top bar */}
        <div className="px-4 pt-4 pb-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">Q{question_index + 1}/{question_count}</span>
            <span className={`text-2xl font-black tabular-nums ${secs <= 5 ? "text-red-400" : secs <= 10 ? "text-orange-400" : "text-green-400"}`}>
              {secs}
            </span>
          </div>
          <div className="h-2 bg-white/10 rounded-full overflow-hidden">
            <div className="h-2 rounded-full transition-all"
              style={{
                width: `${pct * 100}%`,
                backgroundColor: secs <= 5 ? "#ef4444" : secs <= 10 ? "#f97316" : "#22c55e",
                transition: "width 0.5s linear",
              }} />
          </div>
        </div>

        {/* Question */}
        {q && (
          <div className="px-4 py-4 flex-1 flex flex-col gap-4">
            <div className="bg-white/10 rounded-2xl p-5 text-center">
              <RichTextViewer content={q.prompt_json} className="text-lg font-semibold text-white leading-relaxed" />
            </div>

            {/* Already answered overlay */}
            {hasAnswered ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-4">
                <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-white font-semibold">Answer submitted!</p>
                <p className="text-gray-400 text-sm">Waiting for results…</p>
              </div>
            ) : (
              <>
                {/* Multiple choice options */}
                {q.type === "multiple_choice" && Array.isArray(q.options_json) && (
                  <div className="grid grid-cols-2 gap-3">
                    {q.options_json.map((opt: any, i: number) => (
                      <button
                        key={opt.id}
                        onClick={() => submitAnswer({ selected: opt.id })}
                        className="rounded-2xl p-5 text-white font-bold text-left flex items-start gap-3 active:scale-95 transition-transform"
                        style={{ backgroundColor: OPTION_COLORS[i % OPTION_COLORS.length] }}
                      >
                        <span className="w-8 h-8 rounded-lg bg-black/20 flex items-center justify-center text-sm font-bold shrink-0 mt-0.5">
                          {OPTION_LABELS[i]}
                        </span>
                        <RichTextViewer content={opt.content_json} className="text-white text-sm" />
                      </button>
                    ))}
                  </div>
                )}

                {/* True/False */}
                {q.type === "true_false" && (
                  <div className="grid grid-cols-2 gap-3">
                    {[{ label: "True", val: "true" }, { label: "False", val: "false" }].map((o, i) => (
                      <button
                        key={o.val}
                        onClick={() => submitAnswer({ selected: o.val })}
                        className="rounded-2xl py-10 text-white font-bold text-2xl text-center active:scale-95 transition-transform"
                        style={{ backgroundColor: OPTION_COLORS[i] }}
                      >
                        {o.label}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {error && <p className="text-red-400 text-xs px-4 pb-3">{error}</p>}
      </div>
    );
  }

  // ── Question Closed ────────────────────────────────────────────────────────
  if (state === "question_closed") {
    const correct = gameState.correct_answer;
    const opts = gameState.options_json ?? [];

    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-start p-6 gap-6">
        {/* Player result */}
        {playerResult && (
          <div className={`w-full max-w-sm rounded-2xl p-6 text-center space-y-2 ${
            playerResult.is_correct ? "bg-green-500/20 border border-green-500/40" : "bg-red-500/20 border border-red-500/40"
          }`}>
            <p className="text-4xl">{playerResult.is_correct ? "✓" : "✗"}</p>
            <p className="text-xl font-bold">{playerResult.is_correct ? "Correct!" : "Incorrect"}</p>
            {playerResult.is_correct && (
              <p className="text-3xl font-black text-amber-400">+{playerResult.points_earned.toLocaleString()}</p>
            )}
            <p className="text-gray-300 text-sm">
              Total: <span className="font-bold text-white">{playerResult.total_score.toLocaleString()} pts</span>
              {" · "}Rank: <span className="font-bold text-white">#{playerResult.rank}</span>
            </p>
          </div>
        )}

        {!playerResult && (
          <div className="w-full max-w-sm rounded-2xl p-6 text-center bg-white/10">
            <p className="text-gray-400 text-sm">Loading result…</p>
          </div>
        )}

        {/* Correct answer */}
        {opts.length > 0 && (
          <div className="w-full max-w-sm space-y-2">
            {opts.map((opt: any, i: number) => {
              const isCorrect = correct === opt.id || correct?.value === opt.id;
              return (
                <div key={opt.id}
                  className={`rounded-xl p-3 flex items-center gap-3 transition ${isCorrect ? "opacity-100" : "opacity-30"}`}
                  style={{ backgroundColor: OPTION_COLORS[i % OPTION_COLORS.length] }}>
                  <span className="w-7 h-7 rounded-md bg-black/20 flex items-center justify-center text-xs font-bold shrink-0">
                    {OPTION_LABELS[i]}
                  </span>
                  <RichTextViewer content={opt.content_json} className="text-white text-sm font-medium" />
                  {isCorrect && <span className="ml-auto text-white font-bold">✓</span>}
                </div>
              );
            })}
          </div>
        )}

        {/* True/False answer */}
        {opts.length === 0 && (correct === "true" || correct === "false" || correct?.value) && (
          <div className="w-full max-w-sm space-y-2">
            {[{ label: "True", val: "true" }, { label: "False", val: "false" }].map((o, i) => {
              const isCorrect = correct === o.val || correct?.value === o.val;
              return (
                <div key={o.val}
                  className={`rounded-xl p-5 text-white font-bold text-xl text-center transition ${isCorrect ? "opacity-100" : "opacity-30"}`}
                  style={{ backgroundColor: OPTION_COLORS[i] }}>
                  {o.label} {isCorrect && "✓"}
                </div>
              );
            })}
          </div>
        )}

        <p className="text-gray-500 text-sm">Waiting for host to continue…</p>
      </div>
    );
  }

  // ── Finished ───────────────────────────────────────────────────────────────
  if (state === "finished") {
    const top = gameState.top_cumulative ?? [];
    const myEntry = top.find((e) => e.nickname === nickname);

    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-start p-6 gap-6">
        <h1 className="text-3xl font-black mt-4">Game Over!</h1>

        {myEntry && (
          <div className={`w-full max-w-sm rounded-2xl p-6 text-center space-y-2 ${
            myEntry.rank <= 3 ? "bg-amber-500/20 border border-amber-500/40" : "bg-white/10"
          }`}>
            <p className="text-4xl">
              {myEntry.rank === 1 ? "🥇" : myEntry.rank === 2 ? "🥈" : myEntry.rank === 3 ? "🥉" : "🎉"}
            </p>
            <p className="text-xl font-bold">{nickname}</p>
            <p className="text-3xl font-black text-amber-400">{myEntry.total_score.toLocaleString()} pts</p>
            <p className="text-gray-400">Rank #{myEntry.rank} of {top.length}</p>
          </div>
        )}

        <div className="w-full max-w-sm space-y-2">
          {top.map((entry) => (
            <div key={entry.nickname}
              className={`flex items-center gap-3 rounded-xl px-4 py-3 ${
                entry.nickname === nickname ? "bg-amber-500/20 border border-amber-500/30" :
                entry.rank <= 3 ? "bg-white/10" : "bg-white/5"
              }`}>
              <span className="text-base font-bold w-6 text-center text-gray-400">
                {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `#${entry.rank}`}
              </span>
              <span className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                style={{ backgroundColor: entry.avatar_color }}>
                {entry.nickname[0]?.toUpperCase()}
              </span>
              <span className="text-sm font-medium truncate">{entry.nickname}</span>
              <span className="ml-auto font-bold text-amber-400">{entry.total_score.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
