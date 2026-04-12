"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import RichTextEditor from "@/components/RichTextEditor";
import RichTextViewer, { tiptapToText } from "@/components/RichTextViewer";

// ── Block context editor (collapsible) ────────────────────────────────────────

function BlockContextEditor({ value, onChange, editorKey, blockTitle }: {
  value: any; onChange: (json: any) => void; editorKey: number; blockTitle: string;
}) {
  const [open, setOpen] = useState(!!value);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const firstNode = value?.content?.[0];
  const isMediaContext = firstNode?.type === "audio" || firstNode?.type === "video";
  const mediaType = firstNode?.type as "audio" | "video" | undefined;
  const mediaAttrs = isMediaContext ? firstNode.attrs : null;

  async function handleFileUpload(file: File) {
    setUploading(true);
    setUploadError("");
    try {
      const data = new FormData();
      data.append("file", file);
      const res = await api.post("/media", data, { headers: { "Content-Type": "multipart/form-data" } });
      const { id, mime_type } = res.data;
      const nodeType = mime_type.startsWith("video/") ? "video" : "audio";
      onChange({
        type: "doc",
        content: [{ type: nodeType, attrs: { media_file_id: id, mime_type, text: blockTitle || "" } }],
      });
    } catch {
      setUploadError("Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const contextBadge = isMediaContext
    ? <span className="ml-1 text-amber-600 font-normal">({mediaType})</span>
    : null;

  return (
    <div className="border border-gray-100 rounded-lg">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left px-3 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 flex items-center justify-between"
      >
        <span>Block context{contextBadge} <span className="font-normal text-gray-400">(optional — shared passage or audio/video shown above all questions)</span></span>
        <span className="text-gray-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-3 border-t border-gray-100 space-y-2">
          {isMediaContext ? (
            /* Media file set — show badge + replace/remove */
            <>
              <div className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2">
                <span className="text-gray-500 text-sm">{mediaType === "audio" ? "♪" : "▶"}</span>
                <span className="flex-1 text-xs text-gray-700">{mediaAttrs?.mime_type}</span>
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="text-xs text-indigo-600 hover:underline" disabled={uploading}>
                  {uploading ? "Uploading…" : "Replace"}
                </button>
                <button type="button" onClick={() => onChange(null)}
                  className="text-xs text-red-400 hover:underline">Remove</button>
              </div>
              <input ref={fileInputRef} type="file" accept="audio/*,video/*" className="hidden"
                onChange={async (e) => { const f = e.target.files?.[0]; if (f) await handleFileUpload(f); e.target.value = ""; }} />
              {uploadError && <p className="text-xs text-red-500">{uploadError}</p>}
            </>
          ) : (
            /* Text passage + upload option */
            <>
              <RichTextEditor
                key={`ctx-${editorKey}`}
                value={value}
                onChange={onChange}
                placeholder="Passage, instructions, or image shown above all questions in this block…"
              />
              <div className="flex items-center justify-between">
                {value
                  ? <button type="button" onClick={() => onChange(null)} className="text-xs text-red-400 hover:underline">Clear context</button>
                  : <span className="text-xs text-gray-400">No context set — block title spoken by TTS on spelling tests.</span>
                }
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="text-xs text-indigo-600 hover:underline" disabled={uploading}>
                  {uploading ? "Uploading…" : "↑ Upload audio / video"}
                </button>
              </div>
              <input ref={fileInputRef} type="file" accept="audio/*,video/*" className="hidden"
                onChange={async (e) => { const f = e.target.files?.[0]; if (f) await handleFileUpload(f); e.target.value = ""; }} />
              {uploadError && <p className="text-xs text-red-500">{uploadError}</p>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Types ─────────────────────────────────────────────────────────────────────

type QuestionData = {
  id: string; type: string; prompt_json: any;
  options_json: any; correct_answer: any; explanation_json: any;
  points: number; tags: string[];
};

type BlockQuestion = { question_id: string; order: number; data: QuestionData };
type Block = { title: string; context_json: any; questions: BlockQuestion[] };

type QFormState = {
  blockIdx: number;
  editingId: string | null;
  type: string;
  prompt_json: any;
  options: { id: string; text: string }[];
  correct_answer: string;
  explanation_json: any;
  points: number;
  tags: string;
  media_file_id: string;
  media_mime_type: string;
};

const QUESTION_TYPES = [
  "multiple_choice", "multiple_select", "true_false",
  "short_text", "long_text",
];

const defaultSettings = {
  title: "", description: "", mode: "async", access: "open",
  time_limit_minutes: "", allow_multiple_attempts: false, max_attempts: "",
  randomize_questions: false, randomize_options: false,
  show_score: "at_end", show_correct_answers: "never",
  passing_score_pct: "", multiple_select_scoring: "all_or_nothing",
  draw_count: "", available_from: "", available_until: "",
  practice_enabled: false,
};

function emptyQForm(blockIdx: number): QFormState {
  return {
    blockIdx, editingId: null,
    type: "multiple_choice",
    prompt_json: null,
    options: [{ id: "a", text: "" }, { id: "b", text: "" }],
    correct_answer: "",
    explanation_json: null,
    points: 1, tags: "",
    media_file_id: "", media_mime_type: "",
  };
}

function questionToForm(blockIdx: number, q: QuestionData): QFormState {
  const opts = Array.isArray(q.options_json)
    ? q.options_json.map((o: any) => ({
        id: o.id,
        text: o.content_json?.content?.[0]?.content?.[0]?.text ?? "",
      }))
    : [];
  const isMedia = ["audio_prompt", "video_prompt"].includes(q.type);
  const mediaRef = isMedia && !Array.isArray(q.options_json) ? q.options_json : null;
  return {
    blockIdx, editingId: q.id,
    type: q.type,
    prompt_json: q.prompt_json,
    options: opts.length ? opts : [{ id: "a", text: "" }],
    correct_answer: q.type === "short_text"
      ? (q.correct_answer?.text ?? "")
      : typeof q.correct_answer === "string"
        ? q.correct_answer
        : JSON.stringify(q.correct_answer ?? ""),
    explanation_json: q.explanation_json,
    points: q.points,
    tags: (q.tags || []).join(", "),
    media_file_id: mediaRef?.media_file_id ?? "",
    media_mime_type: mediaRef?.mime_type ?? "",
  };
}

// ── Main component ────────────────────────────────────────────────────────────

type Props = { testId?: string };

export default function TestForm({ testId }: Props) {
  const router = useRouter();
  const [settings, setSettings] = useState(defaultSettings);
  const [blocks, setBlocks] = useState<Block[]>([{ title: "", context_json: null, questions: [] }]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Inline question form
  const [qForm, setQForm] = useState<QFormState | null>(null);
  const [qSaving, setQSaving] = useState(false);
  const [qError, setQError] = useState("");
  const [editorKey, setEditorKey] = useState(0);

  // Bulk import
  const [importingQuestions, setImportingQuestions] = useState(false);
  const [importQMsg, setImportQMsg] = useState("");
  const importQRef = useRef<HTMLInputElement>(null);

  const isRandomMode = !!settings.draw_count;
  const totalQuestions = blocks.reduce((n, b) => n + b.questions.length, 0);

  useEffect(() => {
    if (!testId) return;
    api.get(`/tests/${testId}`).then((r) => {
      const t = r.data;
      setSettings({
        title: t.title, description: t.description ?? "",
        mode: t.mode, access: t.access,
        time_limit_minutes: t.time_limit_minutes ?? "",
        allow_multiple_attempts: t.allow_multiple_attempts,
        max_attempts: t.max_attempts ?? "",
        randomize_questions: t.randomize_questions,
        randomize_options: t.randomize_options,
        show_score: t.show_score, show_correct_answers: t.show_correct_answers,
        passing_score_pct: t.passing_score_pct ?? "",
        multiple_select_scoring: t.multiple_select_scoring,
        draw_count: t.draw_count ?? "",
        available_from: t.available_from ? t.available_from.slice(0, 16) : "",
        available_until: t.available_until ? t.available_until.slice(0, 16) : "",
        practice_enabled: t.practice_enabled ?? false,
      });
      setBlocks(
        t.blocks.length > 0
          ? t.blocks.map((b: any) => ({
              title: b.title ?? "",
              context_json: b.context_json ?? null,
              questions: b.questions.map((bq: any) => ({
                question_id: bq.question_id,
                order: bq.order,
                data: bq.question,
              })),
            }))
          : [{ title: "", context_json: null, questions: [] }]
      );
    });
  }, [testId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Block management ───────────────────────────────────────────────────────

  function addBlock() {
    setBlocks([...blocks, { title: "", context_json: null, questions: [] }]);
  }

  function removeBlock(i: number) {
    setBlocks(blocks.filter((_, idx) => idx !== i));
  }

  function removeQuestionFromBlock(blockIdx: number, qId: string) {
    setBlocks(blocks.map((b, i) =>
      i !== blockIdx ? b : { ...b, questions: b.questions.filter((q) => q.question_id !== qId) }
    ));
  }

  // ── Inline question form ───────────────────────────────────────────────────

  function openNewQuestion(blockIdx: number) {
    setQError("");
    setEditorKey((k) => k + 1);
    setQForm(emptyQForm(blockIdx));
  }

  function openEditQuestion(blockIdx: number, q: QuestionData) {
    setQError("");
    setEditorKey((k) => k + 1);
    setQForm(questionToForm(blockIdx, q));
  }

  function setQ(key: string, value: any) {
    setQForm((f) => f ? { ...f, [key]: value } : f);
  }

  function addOption() {
    if (!qForm) return;
    const id = String.fromCharCode(97 + qForm.options.length);
    setQ("options", [...qForm.options, { id, text: "" }]);
  }

  function removeOption(idx: number) {
    if (!qForm) return;
    setQ("options", qForm.options.filter((_, i) => i !== idx));
  }

  async function handleMediaUpload(file: File) {
    const data = new FormData();
    data.append("file", file);
    const res = await api.post("/media", data, { headers: { "Content-Type": "multipart/form-data" } });
    setQ("media_file_id", res.data.id);
    setQ("media_mime_type", res.data.mime_type);
  }

  async function handleSaveQuestion() {
    if (!qForm) return;
    setQSaving(true);
    setQError("");
    try {
      const hasOptions = ["multiple_choice", "multiple_select", "true_false"].includes(qForm.type);
      const isMedia = ["audio_prompt", "video_prompt"].includes(qForm.type);

      const payload: any = {
        type: qForm.type,
        prompt_json: qForm.prompt_json,
        points: qForm.points,
        tags: qForm.tags.split(",").map((t) => t.trim()).filter(Boolean),
        explanation_json: qForm.explanation_json || undefined,
      };
      if (hasOptions) {
        payload.options = qForm.options;
        payload.correct_answer = qForm.correct_answer || null;
      }
      if (qForm.type === "short_text") {
        payload.correct_answer = qForm.correct_answer.trim()
          ? { text: qForm.correct_answer.trim() }
          : null;
      }
      if (isMedia && qForm.media_file_id) {
        payload.media_ref = { media_file_id: qForm.media_file_id, mime_type: qForm.media_mime_type };
      }

      const bi = qForm.blockIdx;

      if (qForm.editingId) {
        const res = await api.put(`/questions/${qForm.editingId}`, payload);
        const updated: QuestionData = res.data;
        setBlocks((prev) => prev.map((b, i) =>
          i !== bi ? b : {
            ...b,
            questions: b.questions.map((q) =>
              q.question_id === qForm.editingId ? { ...q, data: updated } : q
            ),
          }
        ));
      } else {
        const res = await api.post("/questions", payload);
        const created: QuestionData = res.data;
        setBlocks((prev) => prev.map((b, i) =>
          i !== bi ? b : {
            ...b,
            questions: [...b.questions, { question_id: created.id, order: b.questions.length, data: created }],
          }
        ));
      }
      setQForm(null);
    } catch (e: any) {
      setQError(e?.response?.data?.detail ?? "Save failed");
    } finally {
      setQSaving(false);
    }
  }

  // ── Bulk import questions ──────────────────────────────────────────────────

  async function handleImportQuestions(file: File) {
    setImportingQuestions(true);
    setImportQMsg("");
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      const res = await api.post("/questions/bulk-import", json);
      const { created, question_ids } = res.data;

      // Fetch the created questions to get their full data
      const newQuestions: QuestionData[] = await Promise.all(
        question_ids.map((id: string) => api.get(`/questions/${id}`).then((r) => r.data))
      );

      setBlocks((prev) => prev.map((b, i) => {
        if (i !== 0) return b;
        const existing = new Set(b.questions.map((q) => q.question_id));
        const newBqs = newQuestions
          .filter((q) => !existing.has(q.id))
          .map((q, idx) => ({ question_id: q.id, order: b.questions.length + idx, data: q }));
        return { ...b, questions: [...b.questions, ...newBqs] };
      }));
      setImportQMsg(`✓ Imported ${created} question${created !== 1 ? "s" : ""} into block 1`);
    } catch (e: any) {
      setImportQMsg(`✗ ${e?.response?.data?.detail ?? "Import failed"}`);
    } finally {
      setImportingQuestions(false);
    }
  }

  // ── Save test ──────────────────────────────────────────────────────────────

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const drawCount = settings.draw_count ? parseInt(settings.draw_count as string) : null;
      const payload = {
        ...settings,
        time_limit_minutes: settings.time_limit_minutes ? parseInt(settings.time_limit_minutes as string) : null,
        max_attempts: settings.max_attempts ? parseInt(settings.max_attempts as string) : null,
        passing_score_pct: settings.passing_score_pct ? parseInt(settings.passing_score_pct as string) : null,
        draw_count: drawCount,
        randomize_questions: drawCount ? false : settings.randomize_questions,
        available_from: settings.available_from || null,
        available_until: settings.available_until || null,
        blocks: blocks.map((b, i) => ({
          title: b.title || null,
          context_json: b.context_json || null,
          order: i,
          questions: b.questions.map((q, j) => ({ question_id: q.question_id, order: j })),
        })),
      };
      if (testId) {
        await api.put(`/tests/${testId}`, payload);
      } else {
        await api.post("/tests", payload);
      }
      router.push("/tests");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Save failed");
    } finally { setSaving(false); }
  }

  function set(key: string, value: any) { setSettings((s) => ({ ...s, [key]: value })); }

  const needsOptions = qForm ? ["multiple_choice", "multiple_select", "true_false"].includes(qForm.type) : false;
  const isMedia = qForm ? ["audio_prompt", "video_prompt"].includes(qForm.type) : false;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl space-y-6">
      {error && <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>}

      {/* Settings */}
      <div className="card space-y-4">
        <h2 className="font-semibold text-gray-800">Settings</h2>
        <div>
          <label className="label">Title</label>
          <input value={settings.title} onChange={(e) => set("title", e.target.value)} className="input w-full" />
        </div>
        <div>
          <label className="label">Description</label>
          <textarea value={settings.description} onChange={(e) => set("description", e.target.value)} rows={2} className="input w-full" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Mode</label>
            <select value={settings.mode} onChange={(e) => set("mode", e.target.value)} className="input w-full">
              <option value="async">Async (self-paced)</option>
              <option value="sync">Sync (scheduled)</option>
            </select>
          </div>
          <div>
            <label className="label">Access</label>
            <select value={settings.access} onChange={(e) => set("access", e.target.value)} className="input w-full">
              <option value="open">Open link</option>
              <option value="registered">Registered users</option>
              <option value="code">Access codes</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Test mode</label>
          <div className="flex gap-4 mt-1">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" name="testMode" checked={!isRandomMode} onChange={() => set("draw_count", "")} />
              <span className="text-gray-700">Fixed sequence</span>
              <span className="text-xs text-gray-400">(same questions, same order)</span>
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" name="testMode" checked={isRandomMode} onChange={() => set("draw_count", "10")} />
              <span className="text-gray-700">Random draw</span>
              <span className="text-xs text-gray-400">(each taker gets different questions)</span>
            </label>
          </div>
          {isRandomMode && (
            <div className="mt-2 flex items-center gap-3">
              <input type="number" min={1} max={totalQuestions || undefined}
                value={settings.draw_count}
                onChange={(e) => set("draw_count", e.target.value)}
                className="input w-24 text-center" />
              <span className="text-sm text-gray-500">
                of <strong>{totalQuestions}</strong> questions per attempt
                {settings.draw_count && totalQuestions > 0 && parseInt(settings.draw_count as string) > totalQuestions && (
                  <span className="ml-2 text-amber-600">⚠ exceeds pool size</span>
                )}
              </span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Time limit (minutes, blank = untimed)</label>
            <input type="number" min={1} value={settings.time_limit_minutes} onChange={(e) => set("time_limit_minutes", e.target.value)} className="input w-full" />
          </div>
          <div>
            <label className="label">Passing score %</label>
            <input type="number" min={0} max={100} value={settings.passing_score_pct} onChange={(e) => set("passing_score_pct", e.target.value)} className="input w-full" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Show score</label>
            <select value={settings.show_score} onChange={(e) => set("show_score", e.target.value)} className="input w-full">
              <option value="at_end">At end</option>
              <option value="never">Never</option>
            </select>
          </div>
          <div>
            <label className="label">Show correct answers</label>
            <select value={settings.show_correct_answers} onChange={(e) => set("show_correct_answers", e.target.value)} className="input w-full">
              <option value="never">Never</option>
              <option value="at_end">At end</option>
              <option value="per_question">Per question</option>
              <option value="after_review">After review</option>
            </select>
          </div>
        </div>
        <div>
          <label className="label">Multiple-select scoring</label>
          <select value={settings.multiple_select_scoring} onChange={(e) => set("multiple_select_scoring", e.target.value)} className="input w-full">
            <option value="all_or_nothing">All or nothing (full points only when all correct)</option>
            <option value="partial">Partial credit (proportional to correct selections)</option>
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Available from (optional)</label>
            <input type="datetime-local" value={settings.available_from} onChange={(e) => set("available_from", e.target.value)} className="input w-full" />
          </div>
          <div>
            <label className="label">Available until (optional)</label>
            <input type="datetime-local" value={settings.available_until} onChange={(e) => set("available_until", e.target.value)} className="input w-full" />
          </div>
        </div>

        {!isRandomMode && (
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={settings.randomize_questions} onChange={(e) => set("randomize_questions", e.target.checked)} />
              Randomize question order
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input type="checkbox" checked={settings.randomize_options} onChange={(e) => set("randomize_options", e.target.checked)} />
              Randomize option order
            </label>
          </div>
        )}

        <div className="border-t border-gray-100 pt-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" checked={settings.practice_enabled as boolean} onChange={(e) => set("practice_enabled", e.target.checked)} className="w-4 h-4 accent-amber-500" />
            <div>
              <p className="text-sm font-medium text-gray-800">Enable practice mode</p>
              <p className="text-xs text-gray-500">Allows the Quizbee mobile app to download this test as a practice bundle via QR code.</p>
            </div>
          </label>
        </div>
      </div>

      {/* Blocks / Questions */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">
            Questions
            {isRandomMode && totalQuestions > 0 && (
              <span className="ml-2 text-sm font-normal text-amber-600">
                ({totalQuestions} in pool · drawing {settings.draw_count || "?"} per attempt)
              </span>
            )}
          </h2>
          <div className="flex items-center gap-3">
            <button onClick={() => importQRef.current?.click()} disabled={importingQuestions}
              className="text-sm text-indigo-600 hover:underline disabled:opacity-50">
              {importingQuestions ? "Importing…" : "↑ Import questions"}
            </button>
            <input ref={importQRef} type="file" accept=".json,application/json" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportQuestions(f); e.target.value = ""; }} />
            <button onClick={addBlock} className="text-sm text-amber-600 hover:underline">+ Add block</button>
          </div>
        </div>

        {importQMsg && (
          <p className={`text-xs px-3 py-2 rounded ${importQMsg.startsWith("✓") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
            {importQMsg}
          </p>
        )}

        {blocks.map((block, bi) => (
          <div key={bi} className="card space-y-3">
            <div className="flex items-center justify-between">
              <input value={block.title}
                onChange={(e) => setBlocks(blocks.map((b, i) => i === bi ? { ...b, title: e.target.value } : b))}
                placeholder={`Block ${bi + 1} title (optional)`}
                className="input flex-1 mr-3" />
              {blocks.length > 1 && (
                <button onClick={() => removeBlock(bi)} className="text-xs text-red-400 hover:underline shrink-0">Remove block</button>
              )}
            </div>

            {/* Block context editor */}
            <BlockContextEditor
              value={block.context_json}
              onChange={(json) => setBlocks(blocks.map((b, i) => i === bi ? { ...b, context_json: json } : b))}
              editorKey={bi}
              blockTitle={block.title}
            />

            {block.questions.length > 0 && (
              <ul className="space-y-1">
                {block.questions.map((bq) => (
                  <li key={bq.question_id} className="flex items-center justify-between text-sm bg-gray-50 rounded px-3 py-1.5 group">
                    <button
                      onClick={() => openEditQuestion(bi, bq.data)}
                      className="flex-1 text-left truncate hover:text-amber-700"
                    >
                      <span className="text-xs text-amber-600 mr-2">{bq.data?.type}</span>
                      <span className="text-gray-700">{bq.data ? tiptapToText(bq.data.prompt_json).slice(0, 80) || "(no prompt)" : bq.question_id}</span>
                    </button>
                    <button onClick={() => removeQuestionFromBlock(bi, bq.question_id)}
                      className="text-red-400 text-xs ml-2 shrink-0 opacity-0 group-hover:opacity-100">✕</button>
                  </li>
                ))}
              </ul>
            )}

            <button onClick={() => openNewQuestion(bi)}
              className="text-sm text-amber-600 hover:underline">
              + New question
            </button>
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-3">
        <button onClick={() => router.push("/tests")} className="btn-ghost">Cancel</button>
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? "Saving…" : "Save Test"}
        </button>
      </div>

      {/* Inline question form modal */}
      {qForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-bold">{qForm.editingId ? "Edit Question" : "New Question"}</h2>
            {qError && <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{qError}</p>}

            <div>
              <label className="label">Type</label>
              <select value={qForm.type} onChange={(e) => setQ("type", e.target.value)} className="input w-full">
                {QUESTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            {qForm.type !== "divider" && (
              <div>
                <label className="label">Prompt</label>
                <RichTextEditor
                  key={editorKey}
                  value={qForm.prompt_json}
                  onChange={(json) => setQ("prompt_json", json)}
                  placeholder="Question prompt…"
                />
              </div>
            )}

            {qForm.type === "short_text" && (
              <div>
                <label className="label">Correct answer (exact match, case-insensitive)</label>
                <input
                  value={qForm.correct_answer}
                  onChange={(e) => setQ("correct_answer", e.target.value)}
                  className="input w-full"
                  placeholder='e.g. "necessary" for a spelling question'
                />
              </div>
            )}

            {isMedia && (
              <div>
                <label className="label">Media file</label>
                {qForm.media_file_id && (
                  <p className="text-xs text-green-600 mb-1">✓ File uploaded ({qForm.media_mime_type})</p>
                )}
                <input type="file" accept={qForm.type === "audio_prompt" ? "audio/*" : "video/*"}
                  className="text-sm"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      try { await handleMediaUpload(file); }
                      catch { setQError("Media upload failed"); }
                    }
                  }} />
              </div>
            )}

            {needsOptions && (
              <div>
                <label className="label">Options</label>
                {qForm.options.map((opt, i) => (
                  <div key={i} className="flex gap-2 mb-1">
                    <input value={opt.id}
                      onChange={(e) => {
                        const opts = [...qForm.options]; opts[i] = { ...opts[i], id: e.target.value };
                        setQ("options", opts);
                      }}
                      className="input w-16" placeholder="id" />
                    <input value={opt.text}
                      onChange={(e) => {
                        const opts = [...qForm.options]; opts[i] = { ...opts[i], text: e.target.value };
                        setQ("options", opts);
                      }}
                      className="input flex-1" placeholder="Option text" />
                    <button onClick={() => removeOption(i)} className="text-red-400 text-xs px-1">✕</button>
                  </div>
                ))}
                <button onClick={addOption} className="text-xs text-amber-600 hover:underline mt-1">+ Add option</button>
              </div>
            )}

            {needsOptions && (
              <div>
                <label className="label">Correct answer (option id)</label>
                <input value={qForm.correct_answer}
                  onChange={(e) => setQ("correct_answer", e.target.value)}
                  className="input w-full"
                  placeholder='e.g. "a" or ["a","b"] for multiple_select' />
              </div>
            )}

            <div className="flex gap-3">
              <div className="flex-1">
                <label className="label">Points</label>
                <input type="number" min={1} value={qForm.points}
                  onChange={(e) => setQ("points", parseInt(e.target.value) || 1)}
                  className="input w-full" />
              </div>
              <div className="flex-1">
                <label className="label">Tags (comma separated)</label>
                <input value={qForm.tags} onChange={(e) => setQ("tags", e.target.value)}
                  className="input w-full" placeholder="grammar, reading" />
              </div>
            </div>

            <div>
              <label className="label">Explanation (shown in practice mode)</label>
              <RichTextEditor
                key={editorKey + 1000}
                value={qForm.explanation_json}
                onChange={(json) => setQ("explanation_json", json)}
                placeholder="Explanation for correct answer…"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setQForm(null)} className="btn-ghost">Cancel</button>
              <button onClick={handleSaveQuestion} disabled={qSaving} className="btn-primary disabled:opacity-50">
                {qSaving ? "Saving…" : "Save question"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
