"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import RichTextViewer from "@/components/RichTextViewer";

type SessionSummary = {
  id: string; taker_email: string | null; status: string;
  review_status: string; score_pct: number | null; passed: boolean | null;
  started_at: string; submitted_at: string | null;
};

type AnswerDetail = {
  question_id: string; question_type: string;
  prompt_json: any; options_json: any; correct_answer: any;
  value: any; auto_score: number | null; manual_score: number | null; needs_review: boolean;
};

type SessionDetail = SessionSummary & { answers: AnswerDetail[] };

// ── Answer value display ──────────────────────────────────────────────────────

function takerValue(a: AnswerDetail): string | null {
  if (!a.value) return null;
  if (a.value.selected !== undefined)
    return Array.isArray(a.value.selected) ? a.value.selected.join(", ") : String(a.value.selected);
  if (a.value.text !== undefined) return a.value.text;
  return JSON.stringify(a.value);
}

function isCorrectOption(optId: string, correct_answer: any): boolean {
  if (!correct_answer) return false;
  if (typeof correct_answer === "string") return correct_answer === optId;
  if (Array.isArray(correct_answer)) return correct_answer.includes(optId);
  return false;
}

function isTakerSelected(optId: string, value: any): boolean {
  if (!value) return false;
  if (typeof value.selected === "string") return value.selected === optId;
  if (Array.isArray(value.selected)) return value.selected.includes(optId);
  return false;
}

// ── Detail modal ──────────────────────────────────────────────────────────────

function AnswerRow({ a, idx }: { a: AnswerDetail; idx: number }) {
  const hasOptions = Array.isArray(a.options_json) && a.options_json.length > 0;
  const plainValue = takerValue(a);
  const isInfoOnly = ["passage", "divider", "audio_prompt", "video_prompt"].includes(a.question_type);

  return (
    <div className="bg-gray-50 rounded-xl px-4 py-3 space-y-2">
      {/* Header */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-gray-400">Q{idx + 1}</span>
        <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">{a.question_type}</span>
        {a.auto_score !== null && !isInfoOnly && (
          <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${a.auto_score > 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
            {a.auto_score > 0 ? `✓ ${a.auto_score} pt${a.auto_score !== 1 ? "s" : ""}` : "✗ 0 pts"}
          </span>
        )}
        {a.needs_review && (
          <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">Needs review</span>
        )}
      </div>

      {/* Prompt */}
      <RichTextViewer content={a.prompt_json} className="text-sm font-medium text-gray-800" />

      {/* Options — choice types */}
      {hasOptions && (
        <div className="space-y-1 mt-1">
          {a.options_json.map((opt: any) => {
            const correct = isCorrectOption(opt.id, a.correct_answer);
            const selected = isTakerSelected(opt.id, a.value);
            let cls = "border-gray-200 text-gray-600";
            if (correct && selected) cls = "border-green-400 bg-green-50 text-green-800";
            else if (correct) cls = "border-green-300 bg-green-50 text-green-700";
            else if (selected) cls = "border-red-300 bg-red-50 text-red-700";
            return (
              <div key={opt.id} className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-sm ${cls}`}>
                <span className="font-medium shrink-0">{opt.id}.</span>
                <RichTextViewer content={opt.content_json} className="flex-1" />
                {correct && <span className="text-xs shrink-0">✓ correct</span>}
                {selected && !correct && <span className="text-xs shrink-0">← taker</span>}
                {correct && selected && <span className="text-xs shrink-0">← taker</span>}
              </div>
            );
          })}
        </div>
      )}

      {/* True/false */}
      {a.question_type === "true_false" && (
        <div className="flex gap-3 mt-1">
          {["true", "false"].map((v) => {
            const correct = String(a.correct_answer?.value ?? a.correct_answer) === v;
            const selected = a.value?.selected === v;
            let cls = "border-gray-200 text-gray-500";
            if (correct && selected) cls = "border-green-400 bg-green-50 text-green-800";
            else if (correct) cls = "border-green-300 bg-green-50 text-green-700";
            else if (selected) cls = "border-red-300 bg-red-50 text-red-700";
            return (
              <div key={v} className={`flex-1 text-center py-2 rounded-lg border text-sm font-medium ${cls}`}>
                {v === "true" ? "True" : "False"}
                {correct && " ✓"}
              </div>
            );
          })}
        </div>
      )}

      {/* Short/long text */}
      {(a.question_type === "short_text" || a.question_type === "long_text") && plainValue !== null && (
        <div className="mt-1">
          <p className="text-xs text-gray-400 mb-0.5">Taker&apos;s answer:</p>
          <p className="text-sm text-gray-700 bg-white border border-gray-200 rounded px-3 py-2">{plainValue}</p>
          {a.correct_answer?.text && (
            <p className="text-xs text-green-600 mt-1">✓ Expected: <strong>{a.correct_answer.text}</strong></p>
          )}
        </div>
      )}

      {/* No answer */}
      {!isInfoOnly && plainValue === null && !hasOptions && a.question_type !== "true_false" && (
        <p className="text-xs text-gray-400 italic">No answer submitted</p>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type TestOption = { id: string; title: string; published_at: string | null };

function ResultsContent() {
  const params = useSearchParams();
  const testId = params.get("test_id") ?? "";
  const [tests, setTests] = useState<TestOption[]>([]);
  const [activeTestId, setActiveTestId] = useState(testId);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selected, setSelected] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(false);

  // Load test list for the picker
  useEffect(() => {
    api.get("/tests").then((r) => setTests(r.data)).catch(() => {});
  }, []);

  // Sync picker with URL param on mount
  useEffect(() => { if (testId) setActiveTestId(testId); }, [testId]);

  async function load(id: string) {
    if (!id) return;
    setLoading(true);
    try { setSessions((await api.get("/results", { params: { test_id: id } })).data); }
    finally { setLoading(false); }
  }

  useEffect(() => { setSessions([]); load(activeTestId); }, [activeTestId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function openDetail(id: string) {
    const res = await api.get(`/results/${id}`);
    setSelected(res.data);
  }

  function handleExport() {
    const url = `${process.env.NEXT_PUBLIC_API_URL}/results/export/csv?test_id=${activeTestId}`;
    window.open(url, "_blank");
  }

  const activeTestTitle = tests.find((t) => t.id === activeTestId)?.title ?? "";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Results</h1>
        {activeTestId && sessions.length > 0 && (
          <button onClick={handleExport} className="btn-primary">Export CSV</button>
        )}
      </div>

      {/* Test picker */}
      <div className="mb-6">
        <select
          value={activeTestId}
          onChange={(e) => setActiveTestId(e.target.value)}
          className="w-full max-w-sm border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-amber-300"
        >
          <option value="">— Select a test —</option>
          {tests.map((t) => (
            <option key={t.id} value={t.id}>{t.title}{!t.published_at ? " (draft)" : ""}</option>
          ))}
        </select>
      </div>

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && activeTestId && sessions.length === 0 && (
        <p className="text-gray-400 text-sm">No submissions yet for this test.</p>
      )}

      {sessions.length > 0 && (
        <div className="space-y-2">
          {sessions.map((s) => (
            <div key={s.id} className="card flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">{s.taker_email ?? "Anonymous"}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {s.status} · {s.review_status}
                  {s.score_pct !== null ? ` · ${s.score_pct}%` : ""}
                  {s.passed !== null ? (s.passed ? " · Passed ✓" : " · Failed") : ""}
                  {" · "}{new Date(s.started_at).toLocaleString()}
                </p>
              </div>
              <button onClick={() => openDetail(s.id)} className="text-xs text-blue-600 hover:underline shrink-0">View</button>
            </div>
          ))}
        </div>
      )}

      {/* Detail modal */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-bold">{selected.taker_email ?? "Anonymous"}</h2>
                <p className="text-xs text-gray-400">
                  {selected.status} · {selected.review_status}
                  {selected.score_pct !== null ? ` · ${selected.score_pct}%` : ""}
                  {selected.passed !== null ? (selected.passed ? " · Passed ✓" : " · Failed") : ""}
                </p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-700 text-lg">✕</button>
            </div>
            <div className="space-y-3">
              {selected.answers.map((a, i) => (
                <AnswerRow key={a.question_id} a={a} idx={i} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<p className="text-gray-400 text-sm p-8">Loading…</p>}>
      <ResultsContent />
    </Suspense>
  );
}
