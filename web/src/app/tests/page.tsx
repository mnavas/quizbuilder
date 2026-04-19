"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import QRCode from "qrcode";
import { api } from "@/lib/api";
import RichTextViewer, { tiptapToText } from "@/components/RichTextViewer";

type Test = {
  id: string; title: string; mode: string; access: string;
  published_at: string | null; link_token: string | null;
  draw_count: number | null; practice_enabled: boolean;
  blocks: { questions: any[] }[];
};

type PreviewQuestion = {
  id: string; type: string; prompt_json: any;
  options_json: any; correct_answer: any; explanation_json: any; points: number;
};
type PreviewBlock = { title: string | null; order: number; context_json: any; questions: PreviewQuestion[] };
type PreviewData = { id: string; title: string; blocks: PreviewBlock[] };

function questionCount(test: Test) {
  return test.blocks.reduce((n, b) => n + b.questions.length, 0);
}

// ── Preview modal ─────────────────────────────────────────────────────────────

function PreviewModal({ testId, onClose }: { testId: string; onClose: () => void }) {
  const [data, setData] = useState<PreviewData | null>(null);
  const [current, setCurrent] = useState(0);
  const [blockIdx, setBlockIdx] = useState(0);

  useEffect(() => {
    api.get(`/tests/${testId}/preview`).then((r) => setData(r.data));
  }, [testId]);

  if (!data) return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 text-gray-400 text-sm">Loading preview…</div>
    </div>
  );

  // Flatten all questions across blocks for navigation
  const allQuestions: { block: PreviewBlock; q: PreviewQuestion }[] = [];
  for (const block of data.blocks) {
    for (const q of block.questions) {
      allQuestions.push({ block, q });
    }
  }

  if (allQuestions.length === 0) return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 space-y-4">
        <p className="text-gray-500 text-sm">This test has no questions yet.</p>
        <button onClick={onClose} className="btn-primary">Close</button>
      </div>
    </div>
  );

  const { block, q } = allQuestions[current];
  const isInfoOnly = ["passage", "divider", "audio_prompt", "video_prompt"].includes(q.type);

  // options rendered via RichTextViewer below — this is only a fallback for plain text
  function optionFallbackText(o: any): string {
    try { return o.content_json.content[0].content[0].text; } catch { return o.id; }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex flex-col z-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <span className="font-bold text-amber-500">Preview: </span>
          <span className="font-semibold text-gray-800">{data.title}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-400 bg-amber-100 text-amber-700 px-2 py-0.5 rounded font-medium">ADMIN PREVIEW</span>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-lg font-bold">✕</button>
        </div>
      </div>

      {/* Progress */}
      <div className="h-1 bg-gray-200 shrink-0">
        <div className="h-1 bg-amber-500 transition-all" style={{ width: `${((current + 1) / allQuestions.length) * 100}%` }} />
      </div>

      {/* Question */}
      <div className="flex-1 overflow-y-auto flex items-start justify-center p-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 w-full max-w-2xl p-8">
          {block.title && (
            <p className="text-xs font-semibold text-amber-600 uppercase tracking-wide mb-3">{block.title}</p>
          )}

          {/* Block context */}
          {block.context_json && (
            <div className="mb-4 p-3 bg-blue-50 rounded-xl border border-blue-100 text-sm text-blue-700">
              <p className="text-xs font-semibold text-blue-500 uppercase tracking-wide mb-1">Block context</p>
              <RichTextViewer content={block.context_json} className="text-sm text-blue-900" />
            </div>
          )}

          <p className="text-xs text-gray-400 mb-3">
            Question {current + 1} of {allQuestions.length}
            {!isInfoOnly && ` · ${q.points} pt${q.points !== 1 ? "s" : ""}`}
            <span className="ml-2 bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{q.type}</span>
          </p>

          <RichTextViewer content={q.prompt_json} className="text-base text-gray-900 leading-relaxed" />

          {/* Legacy audio_prompt question type */}
          {q.type === "audio_prompt" && (
            <div className="mt-4 p-3 bg-blue-50 rounded-xl text-sm text-blue-600 border border-blue-200">
              🔊 Audio prompt — word will be spoken aloud to taker
              {q.options_json?.media_file_id && (
                <span className="ml-2 text-green-600">(audio file attached)</span>
              )}
              <div className="mt-1 font-semibold text-blue-800">
                Word: {tiptapToText(q.prompt_json)}
              </div>
            </div>
          )}

          {/* Options (choice types) */}
          {Array.isArray(q.options_json) && q.options_json.length > 0 && (
            <div className="space-y-2 mt-4">
              {q.options_json.map((opt: any) => {
                const isCorrect = q.correct_answer === opt.id ||
                  (Array.isArray(q.correct_answer) && q.correct_answer.includes(opt.id));
                return (
                  <div key={opt.id}
                    className={`px-4 py-3 rounded-xl border-2 text-sm ${
                      isCorrect ? "border-green-400 bg-green-50 text-green-800" : "border-gray-200 text-gray-700"
                    }`}>
                    <span className="font-medium mr-2">{opt.id}.</span>
                    <RichTextViewer content={opt.content_json} className="inline" />
                    {isCorrect && <span className="ml-2 text-green-600 text-xs font-semibold">✓ correct</span>}
                  </div>
                );
              })}
            </div>
          )}

          {/* Text input placeholder */}
          {q.type === "short_text" && (
            <div className="mt-4">
              <div className="input w-full text-gray-400 bg-gray-50 border-dashed">Taker types answer here…</div>
              {q.correct_answer?.text && (
                <p className="text-xs text-green-600 mt-1">✓ Auto-scored answer: <strong>{q.correct_answer.text}</strong></p>
              )}
            </div>
          )}
          {q.type === "long_text" && (
            <div className="mt-4 input w-full h-20 text-gray-400 bg-gray-50 border-dashed flex items-start pt-2">
              Taker types answer here…
            </div>
          )}
          {q.type === "true_false" && (
            <div className="flex gap-4 mt-4">
              {["true", "false"].map((v) => (
                <div key={v} className={`flex-1 py-3 rounded-xl border-2 text-sm font-semibold text-center ${
                  String(q.correct_answer?.value ?? q.correct_answer) === v
                    ? "border-green-400 bg-green-50 text-green-700"
                    : "border-gray-200 text-gray-500"
                }`}>
                  {v === "true" ? "True" : "False"}
                  {String(q.correct_answer?.value ?? q.correct_answer) === v && <span className="ml-1 text-xs">✓</span>}
                </div>
              ))}
            </div>
          )}

          {/* Explanation */}
          {q.explanation_json && (
            <div className="mt-5 p-3 bg-amber-50 rounded-xl border border-amber-200">
              <p className="text-xs font-semibold text-amber-700 mb-1">Explanation (shown in practice mode)</p>
              <RichTextViewer content={q.explanation_json} className="text-sm text-amber-900" />
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-between shrink-0">
        <button onClick={() => setCurrent(Math.max(0, current - 1))} disabled={current === 0}
          className="btn-ghost disabled:opacity-30">← Previous</button>
        <span className="text-sm text-gray-400">{current + 1} / {allQuestions.length}</span>
        {current < allQuestions.length - 1 ? (
          <button onClick={() => setCurrent(current + 1)} className="btn-primary">Next →</button>
        ) : (
          <button onClick={onClose} className="btn-primary bg-gray-600 hover:bg-gray-700">Close Preview</button>
        )}
      </div>
    </div>
  );
}

// ── QR Modal ──────────────────────────────────────────────────────────────────

function QrModal({ url, onClose }: { url: string; onClose: () => void }) {
  const [dataUrl, setDataUrl] = useState("");
  useEffect(() => {
    QRCode.toDataURL(url, { width: 280, margin: 2, color: { dark: "#111827", light: "#ffffff" } })
      .then(setDataUrl);
  }, [url]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 shadow-xl max-w-xs w-full text-center"
        onClick={(e) => e.stopPropagation()}>
        <p className="text-sm font-semibold text-gray-700 mb-3">Scan to open the test</p>
        {dataUrl
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={dataUrl} alt="QR code" className="mx-auto rounded-lg" />
          : <div className="w-[280px] h-[280px] mx-auto bg-gray-100 rounded-lg animate-pulse" />}
        <p className="text-xs text-gray-400 mt-3 break-all font-mono">{url}</p>
        <button onClick={onClose}
          className="mt-4 w-full btn-ghost text-sm">Close</button>
      </div>
    </div>
  );
}

// ── Practice QR Modal ─────────────────────────────────────────────────────────

function PracticeQrModal({ testId, baseUrl, onClose }: { testId: string; baseUrl: string; onClose: () => void }) {
  const url = `${baseUrl.replace(/\/$/, "")}/api/v1/tests/${testId}/practice-bundle`;
  const [dataUrl, setDataUrl] = useState("");
  useEffect(() => {
    QRCode.toDataURL(url, { width: 280, margin: 2, color: { dark: "#111827", light: "#ffffff" } })
      .then(setDataUrl);
  }, [url]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl p-6 shadow-xl max-w-xs w-full text-center" onClick={(e) => e.stopPropagation()}>
        <p className="text-sm font-semibold text-gray-700 mb-1">Practice QR</p>
        <p className="text-xs text-gray-400 mb-3">Scan with the Quizbee mobile app to download this bundle.</p>
        {dataUrl
          // eslint-disable-next-line @next/next/no-img-element
          ? <img src={dataUrl} alt="Practice QR code" className="mx-auto rounded-lg" />
          : <div className="w-[280px] h-[280px] mx-auto bg-gray-100 rounded-lg animate-pulse" />}
        <p className="text-xs text-gray-400 mt-3 break-all font-mono">{url}</p>
        <button onClick={onClose} className="mt-4 w-full btn-ghost text-sm">Close</button>
      </div>
    </div>
  );
}

// ── Share Panel ───────────────────────────────────────────────────────────────

const LS_BASE_URL_KEY = "qb_base_url";

function SharePanel({ token }: { token: string }) {
  const [baseUrl, setBaseUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [showQr, setShowQr] = useState(false);

  useEffect(() => {
    setBaseUrl(localStorage.getItem(LS_BASE_URL_KEY) || window.location.origin);
  }, []);

  const fullUrl = `${baseUrl.replace(/\/$/, "")}/take/${token}`;
  const joinUrl = `${baseUrl.replace(/\/$/, "")}/join`;

  function copyLink() {
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="mt-2 pt-2 border-t border-gray-100 space-y-2">
      {/* Board code */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs text-gray-400 shrink-0">Code:</span>
        <span className="font-mono text-xl font-bold tracking-widest text-amber-600 select-all">
          {token}
        </span>
        <span className="text-xs text-gray-400">
          — takers go to <span className="font-mono text-gray-600">{joinUrl}</span>
        </span>
      </div>

      {/* Full link + actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs font-mono text-amber-600 break-all">{fullUrl}</span>
      </div>

      <div className="flex gap-2 pt-1">
        <button onClick={copyLink}
          className={`text-xs px-3 py-1 rounded-md font-medium transition-colors ${copied ? "bg-green-100 text-green-700" : "bg-amber-50 text-amber-700 hover:bg-amber-100"}`}>
          {copied ? "✓ Copied!" : "📋 Copy link"}
        </button>
        <button onClick={() => setShowQr(true)}
          className="text-xs px-3 py-1 rounded-md font-medium bg-gray-100 text-gray-700 hover:bg-gray-200">
          📱 QR Code
        </button>
      </div>

      {showQr && <QrModal url={fullUrl} onClose={() => setShowQr(false)} />}
    </div>
  );
}

// ── Actions dropdown ──────────────────────────────────────────────────────────

function ActionsMenu({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
        aria-label="More actions"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <circle cx="10" cy="4" r="1.5" /><circle cx="10" cy="10" r="1.5" /><circle cx="10" cy="16" r="1.5" />
        </svg>
      </button>
      {open && (
        <div
          className="absolute right-0 top-9 z-20 w-52 bg-white border border-gray-200 rounded-xl shadow-lg py-1"
          onClick={() => setOpen(false)}
        >
          {children}
        </div>
      )}
    </div>
  );
}

function MenuItem({ onClick, href, target, label, danger, disabled }: {
  onClick?: () => void; href?: string; target?: string;
  label: string; danger?: boolean; disabled?: boolean;
}) {
  const cls = `flex w-full items-center px-4 py-2 text-sm transition-colors ${
    danger ? "text-red-600 hover:bg-red-50" :
    disabled ? "text-gray-300 cursor-not-allowed" :
    "text-gray-700 hover:bg-gray-50"
  }`;
  if (href) return (
    <a href={href} target={target} rel="noopener noreferrer" className={cls}>{label}</a>
  );
  return (
    <button onClick={disabled ? undefined : onClick} className={cls} disabled={disabled}>{label}</button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TestsPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [practiceQrId, setPracticeQrId] = useState<string | null>(null);
  const [cloningId, setCloningId] = useState<string | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  useEffect(() => { setBaseUrl(localStorage.getItem("qb_base_url") || window.location.origin); }, []);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    setLoading(true);
    try { setTests((await api.get("/tests")).data); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handlePublish(id: string) {
    try { await api.post(`/tests/${id}/publish`); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Publish failed"); }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this test and all its sessions?")) return;
    await api.delete(`/tests/${id}`);
    load();
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  async function handleExport(id: string, title: string) {
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 30);
    try {
      const res = await api.get(`/tests/${id}/export`, { responseType: "blob" });
      const isZip = res.headers["content-type"]?.includes("zip");
      triggerDownload(res.data, `quizbee_${slug}.${isZip ? "zip" : "json"}`);
    } catch { alert("Export failed"); }
  }

  async function handleOfflineDownload(id: string, title: string) {
    const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "_").slice(0, 30);
    try {
      const res = await api.get(`/tests/${id}/export`, { responseType: "blob" });
      const isZip = res.headers["content-type"]?.includes("zip");
      triggerDownload(res.data, `quizbee_${slug}.${isZip ? "zip" : "json"}`);
    } catch { alert("Download failed"); }
  }

  async function handleClone(id: string) {
    setCloningId(id);
    try { await api.post(`/tests/${id}/clone`); load(); }
    catch (e: any) { alert(e?.response?.data?.detail ?? "Clone failed"); }
    finally { setCloningId(null); }
  }

  async function handleImportCsv(file: File) {
    setImporting(true);
    setImportError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api.post("/tests/import-csv", form, { headers: { "Content-Type": "multipart/form-data" } });
      load();
    } catch (e: any) {
      setImportError(e?.response?.data?.detail ?? "CSV import failed — check the file format");
    } finally { setImporting(false); }
  }

  async function handleImportFile(file: File) {
    setImporting(true);
    setImportError("");
    try {
      if (file.name.endsWith(".zip")) {
        const form = new FormData();
        form.append("file", file);
        await api.post("/tests/import-bundle", form, { headers: { "Content-Type": "multipart/form-data" } });
      } else {
        const text = await file.text();
        const json = JSON.parse(text);
        await api.post("/tests/import", json);
      }
      load();
    } catch (e: any) {
      setImportError(e?.response?.data?.detail ?? "Import failed — check the file format");
    } finally { setImporting(false); }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tests</h1>
        <div className="flex gap-2">
          <button onClick={() => csvInputRef.current?.click()} disabled={importing}
            className="btn-ghost text-sm disabled:opacity-50">
            {importing ? "Importing…" : "↑ CSV"}
          </button>
          <input ref={csvInputRef} type="file" accept=".csv,text/csv" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportCsv(f); e.target.value = ""; }} />
          <button onClick={() => fileInputRef.current?.click()} disabled={importing}
            className="btn-ghost text-sm disabled:opacity-50">
            {importing ? "Importing…" : "↑ Import"}
          </button>
          <input ref={fileInputRef} type="file" accept=".json,.zip,application/json,application/zip" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportFile(f); e.target.value = ""; }} />
          <Link href="/tests/new" className="btn-primary">+ New Test</Link>
        </div>
      </div>

      {importError && (
        <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">{importError}</p>
      )}

      {loading ? <p className="text-gray-400 text-sm">Loading…</p>
        : tests.length === 0 ? (
          <p className="text-gray-400 text-sm">
            No tests yet.{" "}
            <button onClick={() => fileInputRef.current?.click()} className="text-amber-600 hover:underline">
              Import a JSON example
            </button>{" "}
            or create one.
          </p>
        ) : (
          <div className="space-y-3">
            {tests.map((t) => (
              <div key={t.id} className="card space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-gray-900">{t.title}</p>
                      {!t.published_at && (
                        <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-medium">Draft</span>
                      )}
                      {t.practice_enabled && (
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">📱 Practice</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {t.mode} · {t.access} ·{" "}
                      {t.draw_count
                        ? <span className="text-amber-600 font-medium">random · {t.draw_count} of {questionCount(t)}</span>
                        : `${questionCount(t)} questions`}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Link
                      href={`/tests/${t.id}`}
                      className="px-3 py-1.5 text-sm font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors"
                    >
                      Edit
                    </Link>
                    <ActionsMenu>
                      <MenuItem onClick={() => setPreviewId(t.id)} label="Preview" />
                      {t.link_token && (
                        <MenuItem href={`/take/${t.link_token}`} target="_blank" label="Take test" />
                      )}
                      {!t.published_at && (
                        <MenuItem onClick={() => handlePublish(t.id)} label="Publish" />
                      )}
                      <MenuItem href={`/results?test_id=${t.id}`} label="Results" />
                      <MenuItem
                        onClick={() => handleClone(t.id)}
                        label={cloningId === t.id ? "Cloning…" : "Clone"}
                        disabled={cloningId === t.id}
                      />
                      {t.practice_enabled && (
                        <MenuItem onClick={() => setPracticeQrId(t.id)} label="📱 Practice QR" />
                      )}
                      {t.practice_enabled && (
                        <MenuItem onClick={() => handleOfflineDownload(t.id, t.title)} label="↓ Download for app" />
                      )}
                      <MenuItem onClick={() => handleExport(t.id, t.title)} label="↓ Export backup" />
                      <div className="border-t border-gray-100 my-1" />
                      <MenuItem onClick={() => handleDelete(t.id)} label="Delete" danger />
                    </ActionsMenu>
                  </div>
                </div>

                {/* Share panel — visible when published */}
                {t.link_token && <SharePanel token={t.link_token} />}
              </div>
            ))}
          </div>
        )}

      {previewId && <PreviewModal testId={previewId} onClose={() => setPreviewId(null)} />}
      {practiceQrId && <PracticeQrModal testId={practiceQrId} baseUrl={baseUrl} onClose={() => setPracticeQrId(null)} />}
    </div>
  );
}
