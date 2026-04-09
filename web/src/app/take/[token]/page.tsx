"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import RichTextViewer, { tiptapToText } from "@/components/RichTextViewer";

type Option = { id: string; content_json: any };
type Question = {
  id: string; type: string; prompt_json: any;
  options_json: any; points: number; order: number;
  block_title: string | null; context_json: any;
};
type Session = { id: string; test_id: string; status: string; expires_at: string | null; show_correct_answers: string; questions: Question[] };
type PerQuestionFeedback = {
  is_correct: boolean | null;
  needs_review: boolean;
  auto_score: number | null;
  correct_answer: any;
  options_json: any;
};
type AnswerResult = {
  question_id: string; type: string; prompt_json: any;
  options_json: any; correct_answer: any;
  value: any; auto_score: number | null; needs_review: boolean; is_correct: boolean | null;
};
type Result = {
  session_id: string; status: string; score_pct: number | null; passed: boolean | null;
  show_score: boolean; show_correct_answers: string; answers: AnswerResult[];
};

function Timer({ expiresAt, onExpire }: { expiresAt: string; onExpire: () => void }) {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const calc = () => Math.max(0, Math.round((new Date(expiresAt).getTime() - Date.now()) / 1000));
    setSecs(calc());
    const iv = setInterval(() => {
      const s = calc();
      setSecs(s);
      if (s === 0) { clearInterval(iv); onExpire(); }
    }, 1000);
    return () => clearInterval(iv);
  }, [expiresAt]); // eslint-disable-line react-hooks/exhaustive-deps
  const m = Math.floor(secs / 60), s = secs % 60;
  return (
    <span className={`font-mono text-sm ${secs < 60 ? "text-red-600 font-bold" : "text-gray-600"}`}>
      {m}:{String(s).padStart(2, "0")}
    </span>
  );
}

function OptionView({ content_json }: { content_json: any }) {
  return <RichTextViewer content={content_json} className="inline" />;
}

function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);

  function speak() {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = "en-US";
    utt.rate = 0.85;
    utt.onstart = () => setSpeaking(true);
    utt.onend = () => setSpeaking(false);
    utt.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utt);
  }

  return (
    <button
      onClick={speak}
      className={`mt-4 px-8 py-4 rounded-2xl border-2 text-base font-semibold transition ${
        speaking
          ? "border-amber-500 bg-amber-50 text-amber-700"
          : "border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
      }`}
    >
      {speaking ? "🔊 Speaking…" : "🔊 Play word"}
    </button>
  );
}

function AudioPromptPlayer({ mediaRef, promptText, apiBase }: { mediaRef: any; promptText: string; apiBase: string }) {
  // If a real audio file exists, use it. Otherwise fall back to browser SpeechSynthesis.
  if (mediaRef?.media_file_id) {
    const src = `${apiBase}/media/${mediaRef.media_file_id}`;
    // Use src directly on <audio> (not <source> child) and no autoPlay —
    // browsers block autoPlay silently and it can prevent manual play from working.
    return (
      <audio
        controls
        src={src}
        preload="auto"
        className="w-full mt-4 rounded"
      />
    );
  }
  return <SpeakButton text={promptText} />;
}

/**
 * BlockContext — renders the shared context above a block's questions.
 * Handles audio nodes (media_file_id or TTS), video nodes, and falls back
 * to RichTextViewer for text/passage content.
 */
function BlockContext({ context_json, apiBase }: { context_json: any; apiBase: string }) {
  if (!context_json) return null;

  // Check if context is a pure audio node (single audio node doc)
  const nodes: any[] = context_json?.content ?? [];
  const isAudioOnly =
    nodes.length === 1 && nodes[0]?.type === "audio";
  const isVideoOnly =
    nodes.length === 1 && nodes[0]?.type === "video";

  if (isAudioOnly) {
    const attrs = nodes[0].attrs ?? {};
    return (
      <div className="flex flex-col items-center py-4 mb-4 bg-blue-50 rounded-xl border border-blue-100">
        <p className="text-sm text-blue-600 mb-3">Listen carefully:</p>
        <AudioPromptPlayer
          mediaRef={attrs.media_file_id ? { media_file_id: attrs.media_file_id, mime_type: attrs.mime_type ?? "audio/mpeg" } : null}
          promptText={attrs.text ?? ""}
          apiBase={apiBase}
        />
      </div>
    );
  }

  if (isVideoOnly) {
    const attrs = nodes[0].attrs ?? {};
    if (attrs.media_file_id) {
      const src = `${apiBase}/media/${attrs.media_file_id}`;
      return (
        <div className="mb-4">
          <video controls className="w-full rounded-xl max-h-64">
            <source src={src} type={attrs.mime_type ?? "video/mp4"} />
          </video>
        </div>
      );
    }
    return null;
  }

  // Generic rich-text context (passage, heading, etc.)
  return (
    <div className="mb-5 p-4 bg-gray-50 rounded-xl border border-gray-200">
      <RichTextViewer content={context_json} className="text-sm text-gray-800 leading-relaxed" />
    </div>
  );
}

function MediaPlayer({ mediaRef, apiBase }: { mediaRef: any; apiBase: string }) {
  if (!mediaRef?.media_file_id) return null;
  const src = `${apiBase}/media/${mediaRef.media_file_id}`;
  if (mediaRef.mime_type?.startsWith("video/")) {
    return (
      <video controls className="w-full mt-3 rounded max-h-64">
        <source src={src} type={mediaRef.mime_type} />
        Your browser does not support video playback.
      </video>
    );
  }
  return null;
}

export default function TakePage() {
  const { token } = useParams() as { token: string };
  const [email, setEmail] = useState("");
  const [started, setStarted] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [perQuestionFeedback, setPerQuestionFeedback] = useState<Record<string, PerQuestionFeedback>>({});
  const saving = useRef(false);
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

  async function handleStart() {
    setLoading(true); setError("");
    try {
      const res = await api.post(`/sessions/take/${token}`, { taker_email: email || null });
      setSession(res.data);
      setStarted(true);
    } catch (e: any) { setError(e?.response?.data?.detail ?? "Could not start"); }
    finally { setLoading(false); }
  }

  async function saveAnswer(qId: string, value: any) {
    if (!session || saving.current) return;
    saving.current = true;
    try { await api.put(`/sessions/${session.id}/answers/${qId}`, { value }); }
    finally { saving.current = false; }
  }

  async function checkAnswer(qId: string, value: any) {
    if (!session) return;
    try {
      const res = await api.post(`/sessions/${session.id}/check/${qId}`, { value });
      setPerQuestionFeedback((f) => ({ ...f, [qId]: res.data }));
    } catch { /* ignore — feedback is optional */ }
  }

  function handleAnswer(qId: string, value: any) {
    setAnswers((a) => { const next = { ...a, [qId]: value }; saveAnswer(qId, next[qId]); return next; });
  }

  async function handleSubmit() {
    if (!session) return;
    if (!confirm("Submit your answers? This cannot be undone.")) return;
    setLoading(true);
    try {
      const res = await api.post(`/sessions/${session.id}/submit`);
      setResult(res.data);
    } catch (e: any) { setError(e?.response?.data?.detail ?? "Submit failed"); }
    finally { setLoading(false); }
  }

  // Landing
  if (!started) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow p-8 w-full max-w-sm space-y-5">
        <div className="flex items-center justify-center gap-2.5">
          <Image src="/icon-64.png" alt="Quizbee" width={32} height={32} />
          <h1 className="text-2xl font-bold text-amber-500">Quizbee</h1>
        </div>
        <p className="text-sm text-gray-500 text-center">Enter your email to start (optional)</p>
        {error && <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>}
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com (optional)" className="input w-full" />
        <button onClick={handleStart} disabled={loading} className="btn-primary w-full">
          {loading ? "Starting…" : "Start Test →"}
        </button>
      </div>
    </div>
  );

  // Result
  if (result) {
    const showReview = result.show_correct_answers === "at_end" || result.show_correct_answers === "per_question";
    return (
      <div className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Score card */}
          <div className="bg-white rounded-2xl shadow p-8 text-center space-y-3">
            <h1 className="text-2xl font-bold text-gray-900">Test Complete</h1>
            {result.show_score && result.score_pct !== null ? (
              <>
                <p className="text-6xl font-bold text-amber-500">{result.score_pct}%</p>
                {result.passed !== null && (
                  <p className={`text-lg font-semibold ${result.passed ? "text-green-600" : "text-red-500"}`}>
                    {result.passed ? "Passed ✓" : "Not passed"}
                  </p>
                )}
              </>
            ) : (
              <p className="text-gray-500">Your answers have been submitted.</p>
            )}
          </div>

          {/* Per-question review */}
          {showReview && result.answers.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide px-1">Review</h2>
              {result.answers.map((a, i) => {
                const takerText = a.value?.text ?? a.value?.selected ?? null;
                const isMulti = Array.isArray(a.correct_answer);
                return (
                  <div key={a.question_id} className={`bg-white rounded-2xl border-2 p-5 space-y-3 ${
                    a.is_correct === true ? "border-green-300" :
                    a.is_correct === false ? "border-red-300" :
                    "border-gray-100"
                  }`}>
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs text-gray-400">Q{i + 1}</p>
                      {a.is_correct === true && <span className="text-xs font-semibold text-green-600 bg-green-50 px-2 py-0.5 rounded-full">Correct ✓</span>}
                      {a.is_correct === false && <span className="text-xs font-semibold text-red-500 bg-red-50 px-2 py-0.5 rounded-full">Incorrect ✗</span>}
                      {a.needs_review && <span className="text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Needs review</span>}
                    </div>

                    <RichTextViewer content={a.prompt_json} className="text-sm text-gray-800" />

                    {/* Choice options with highlighting */}
                    {Array.isArray(a.options_json) && a.options_json.length > 0 && (
                      <div className="space-y-1.5">
                        {a.options_json.map((opt: any) => {
                          const takerPicked = isMulti
                            ? Array.isArray(takerText) && takerText.includes(opt.id)
                            : takerText === opt.id;
                          const isCorrectOpt = isMulti
                            ? Array.isArray(a.correct_answer) && a.correct_answer.includes(opt.id)
                            : a.correct_answer === opt.id;
                          return (
                            <div key={opt.id} className={`px-3 py-2 rounded-lg border text-sm flex items-center gap-2 ${
                              isCorrectOpt ? "border-green-400 bg-green-50 text-green-800" :
                              takerPicked ? "border-red-300 bg-red-50 text-red-700" :
                              "border-gray-100 text-gray-600"
                            }`}>
                              <span className="font-medium shrink-0">{opt.id}.</span>
                              <RichTextViewer content={opt.content_json} className="inline" />
                              {isCorrectOpt && <span className="ml-auto text-xs text-green-600 shrink-0">✓</span>}
                              {takerPicked && !isCorrectOpt && <span className="ml-auto text-xs text-red-500 shrink-0">✗ your answer</span>}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Text answer */}
                    {(a.type === "short_text" || a.type === "long_text") && (
                      <div className="space-y-1">
                        <p className="text-xs text-gray-400">Your answer:</p>
                        <p className="text-sm text-gray-700 bg-gray-50 rounded px-3 py-2">{takerText ?? <em className="text-gray-400">No answer</em>}</p>
                        {a.correct_answer?.text && (
                          <p className="text-xs text-green-700">Correct: <strong>{a.correct_answer.text}</strong></p>
                        )}
                      </div>
                    )}

                    {/* True/false */}
                    {a.type === "true_false" && (
                      <div className="flex gap-3">
                        {["true", "false"].map((v) => (
                          <div key={v} className={`flex-1 text-center py-2 rounded-lg border text-sm font-medium ${
                            a.correct_answer === v || a.correct_answer?.value === v ? "border-green-400 bg-green-50 text-green-700" :
                            takerText === v ? "border-red-300 bg-red-50 text-red-600" :
                            "border-gray-100 text-gray-500"
                          }`}>
                            {v === "true" ? "True" : "False"}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Exam
  if (!session) return null;
  const questions = session.questions;
  const q = questions[current];
  const totalAnswered = Object.keys(answers).length;
  const isInfoOnly = ["passage", "divider", "audio_prompt", "video_prompt"].includes(q.type);
  const isPerQuestion = session.show_correct_answers === "per_question";
  const feedback = perQuestionFeedback[q.id];

  function renderInput(q: Question) {
    if (q.type === "true_false") return (
      <div className="flex gap-4 mt-4">
        {["true", "false"].map((v) => (
          <button key={v} onClick={() => handleAnswer(q.id, { selected: v })}
            className={`flex-1 py-3 rounded-xl border-2 text-sm font-semibold transition ${answers[q.id]?.selected === v ? "border-amber-500 bg-amber-50 text-amber-700" : "border-gray-200 hover:border-gray-300"}`}>
            {v === "true" ? "True" : "False"}
          </button>
        ))}
      </div>
    );

    if (q.type === "multiple_choice" && Array.isArray(q.options_json)) return (
      <div className="space-y-2 mt-4">
        {q.options_json.map((opt: Option) => (
          <div key={opt.id} role="button" tabIndex={0}
            onClick={() => handleAnswer(q.id, { selected: opt.id })}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleAnswer(q.id, { selected: opt.id }); }}
            className={`w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition cursor-pointer ${answers[q.id]?.selected === opt.id ? "border-amber-500 bg-amber-50 text-amber-700" : "border-gray-200 hover:border-gray-300"}`}>
            <span className="font-medium mr-2">{opt.id}.</span>
            <OptionView content_json={opt.content_json} />
          </div>
        ))}
      </div>
    );

    if (q.type === "multiple_select" && Array.isArray(q.options_json)) {
      const selected: string[] = answers[q.id]?.selected ?? [];
      return (
        <div className="space-y-2 mt-4">
          {q.options_json.map((opt: Option) => {
            const checked = selected.includes(opt.id);
            return (
              <div key={opt.id} role="button" tabIndex={0}
                onClick={() => {
                  const next = checked ? selected.filter((x) => x !== opt.id) : [...selected, opt.id];
                  handleAnswer(q.id, { selected: next });
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    const next = checked ? selected.filter((x) => x !== opt.id) : [...selected, opt.id];
                    handleAnswer(q.id, { selected: next });
                  }
                }}
                className={`w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition cursor-pointer ${checked ? "border-amber-500 bg-amber-50 text-amber-700" : "border-gray-200 hover:border-gray-300"}`}>
                <span className="font-medium mr-2">{opt.id}.</span>
                <OptionView content_json={opt.content_json} />
              </div>
            );
          })}
        </div>
      );
    }

    if (q.type === "short_text") return (
      <input className="input w-full mt-4" value={answers[q.id]?.text ?? ""} placeholder="Your answer…"
        onChange={(e) => handleAnswer(q.id, { text: e.target.value })} />
    );

    if (q.type === "long_text") return (
      <textarea rows={5} className="input w-full mt-4" value={answers[q.id]?.text ?? ""} placeholder="Your answer…"
        onChange={(e) => handleAnswer(q.id, { text: e.target.value })} />
    );

    // passage, divider, audio_prompt, video_prompt — no input
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Image src="/icon-64.png" alt="Quizbee" width={24} height={24} />
          <span className="text-amber-500 font-bold">Quizbee</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400">{totalAnswered}/{questions.length} answered</span>
          {session.expires_at && <Timer expiresAt={session.expires_at} onExpire={handleSubmit} />}
        </div>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-gray-200">
        <div className="h-1 bg-amber-500 transition-all" style={{ width: `${((current + 1) / questions.length) * 100}%` }} />
      </div>

      {/* Question */}
      <div className="flex-1 flex items-start justify-center p-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 w-full max-w-2xl p-8">
          {q.block_title && (
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-3">{q.block_title}</p>
          )}

          {/* Block context — shared content above this question (audio, passage, image, etc.) */}
          {q.context_json && (
            <BlockContext context_json={q.context_json} apiBase={apiBase} />
          )}

          <p className="text-xs text-gray-400 mb-3">
            Question {current + 1} of {questions.length}
            {!isInfoOnly && ` · ${q.points} pt${q.points !== 1 ? "s" : ""}`}
          </p>

          {/* Legacy: audio_prompt question type (backward compat) */}
          {q.type === "audio_prompt" ? (
            <div className="flex flex-col items-center py-4">
              <p className="text-sm text-gray-400 mb-2">Listen carefully, then type the word in the next question.</p>
              <AudioPromptPlayer
                mediaRef={q.options_json}
                promptText={tiptapToText(q.prompt_json)}
                apiBase={apiBase}
              />
            </div>
          ) : (
            <RichTextViewer content={q.prompt_json} className="text-base text-gray-900 leading-relaxed" />
          )}

          {/* Legacy: video_prompt question type (backward compat) */}
          {q.type === "video_prompt" && (
            <MediaPlayer mediaRef={q.options_json} apiBase={apiBase} />
          )}

          {/* Answer input */}
          {renderInput(q)}

          {/* Per-question feedback */}
          {isPerQuestion && !isInfoOnly && feedback && (
            <div className={`mt-4 rounded-xl border-2 p-4 space-y-2 ${
              feedback.is_correct === true ? "border-green-300 bg-green-50" :
              feedback.is_correct === false ? "border-red-300 bg-red-50" :
              "border-amber-200 bg-amber-50"
            }`}>
              {feedback.needs_review ? (
                <p className="text-sm text-amber-700 font-medium">Your answer has been saved and will be reviewed.</p>
              ) : feedback.is_correct ? (
                <p className="text-sm text-green-700 font-semibold">Correct ✓</p>
              ) : (
                <p className="text-sm text-red-600 font-semibold">Incorrect ✗</p>
              )}
              {/* Show correct answer for choice types */}
              {!feedback.needs_review && Array.isArray(feedback.options_json) && feedback.options_json.length > 0 && (
                <div className="space-y-1">
                  {feedback.options_json.map((opt: any) => {
                    const correctAns = feedback.correct_answer;
                    const isCorrectOpt = Array.isArray(correctAns)
                      ? correctAns.includes(opt.id)
                      : correctAns === opt.id || correctAns?.value === opt.id;
                    const takerPicked = (() => {
                      const sel = answers[q.id]?.selected;
                      return Array.isArray(sel) ? sel.includes(opt.id) : sel === opt.id;
                    })();
                    if (!isCorrectOpt && !takerPicked) return null;
                    return (
                      <div key={opt.id} className={`px-3 py-1.5 rounded-lg border text-sm flex items-center gap-2 ${
                        isCorrectOpt ? "border-green-400 bg-white text-green-800" :
                        "border-red-300 bg-white text-red-700"
                      }`}>
                        <span className="font-medium shrink-0">{opt.id}.</span>
                        <RichTextViewer content={opt.content_json} className="inline" />
                        {isCorrectOpt && <span className="ml-auto text-xs text-green-600 shrink-0">✓ correct</span>}
                        {takerPicked && !isCorrectOpt && <span className="ml-auto text-xs text-red-500 shrink-0">✗ your answer</span>}
                      </div>
                    );
                  })}
                </div>
              )}
              {/* Short text correct answer */}
              {!feedback.needs_review && q.type === "short_text" && feedback.correct_answer?.text && !feedback.is_correct && (
                <p className="text-sm text-green-700">Correct answer: <strong>{feedback.correct_answer.text}</strong></p>
              )}
            </div>
          )}

          {/* Check Answer button (per_question mode, before feedback shown) */}
          {isPerQuestion && !isInfoOnly && !feedback && answers[q.id] !== undefined && (
            <button
              onClick={() => checkAnswer(q.id, answers[q.id])}
              className="mt-4 w-full py-2 rounded-xl border-2 border-blue-300 bg-blue-50 text-blue-700 text-sm font-semibold hover:bg-blue-100 transition"
            >
              Check Answer
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-between">
        <button onClick={() => setCurrent(Math.max(0, current - 1))} disabled={current === 0}
          className="btn-ghost disabled:opacity-30">← Previous</button>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {current < questions.length - 1 ? (
          <button onClick={() => setCurrent(current + 1)} className="btn-primary">Next →</button>
        ) : (
          <button onClick={handleSubmit} disabled={loading} className="btn-primary bg-green-600 hover:bg-green-700">
            {loading ? "Submitting…" : "Submit Test"}
          </button>
        )}
      </div>
    </div>
  );
}
