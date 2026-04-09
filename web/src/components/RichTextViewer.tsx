"use client";

import { useMemo } from "react";
import katex from "katex";

interface Props {
  content: any; // Tiptap JSON doc
  className?: string;
}

// ---------------------------------------------------------------------------
// Tiptap JSON → HTML string converter
// ---------------------------------------------------------------------------

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function nodeToHtml(node: any): string {
  if (!node) return "";

  if (node.type === "text") {
    let text = escapeHtml(node.text ?? "");
    const marks: any[] = node.marks ?? [];
    // Apply marks (innermost first)
    for (const mark of marks) {
      switch (mark.type) {
        case "bold":       text = `<strong>${text}</strong>`; break;
        case "italic":     text = `<em>${text}</em>`; break;
        case "underline":  text = `<u>${text}</u>`; break;
        case "strike":     text = `<s>${text}</s>`; break;
        case "code":       text = `<code class="bg-gray-100 px-1 rounded text-xs">${text}</code>`; break;
        case "link":       text = `<a href="${escapeHtml(mark.attrs?.href ?? "#")}" class="text-amber-600 underline" target="_blank" rel="noopener">${text}</a>`; break;
      }
    }
    return text;
  }

  if (node.type === "image") {
    const src = escapeHtml(node.attrs?.src ?? "");
    const alt = escapeHtml(node.attrs?.alt ?? "");
    return `<img src="${src}" alt="${alt}" class="max-w-full rounded my-2" />`;
  }

  const inner = (node.content ?? []).map(nodeToHtml).join("");

  switch (node.type) {
    case "doc":           return inner;
    case "paragraph":     return `<p class="mb-2 last:mb-0">${inner || "<br />"}</p>`;
    case "heading": {
      const level = node.attrs?.level ?? 1;
      const cls = ["", "text-2xl font-bold mt-3 mb-1", "text-xl font-bold mt-2 mb-1", "text-lg font-semibold mt-2 mb-1"][level] ?? "font-bold";
      return `<h${level} class="${cls}">${inner}</h${level}>`;
    }
    case "bulletList":    return `<ul class="list-disc pl-5 mb-2 space-y-0.5">${inner}</ul>`;
    case "orderedList":   return `<ol class="list-decimal pl-5 mb-2 space-y-0.5">${inner}</ol>`;
    case "listItem":      return `<li>${inner}</li>`;
    case "blockquote":    return `<blockquote class="border-l-4 border-gray-300 pl-4 italic text-gray-600 my-2">${inner}</blockquote>`;
    case "codeBlock":     return `<pre class="bg-gray-100 rounded p-3 text-xs font-mono overflow-x-auto my-2"><code>${inner}</code></pre>`;
    case "hardBreak":     return "<br />";
    case "horizontalRule": return '<hr class="my-3 border-gray-300" />';
    default:              return inner;
  }
}

// ---------------------------------------------------------------------------
// KaTeX formula rendering: replace $...$ and $$...$$ in HTML string
// ---------------------------------------------------------------------------

function renderFormulas(html: string): string {
  // Block formulas $$...$$
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (_match, formula) => {
    try {
      return katex.renderToString(formula, { displayMode: true, throwOnError: false });
    } catch {
      return `<span class="text-red-500">$$${formula}$$</span>`;
    }
  });

  // Inline formulas $...$  (single-line only — exclude newlines)
  html = html.replace(/\$([^$\n]+?)\$/g, (_match, formula) => {
    try {
      return katex.renderToString(formula, { displayMode: false, throwOnError: false });
    } catch {
      return `<span class="text-red-500">$${formula}$</span>`;
    }
  });

  return html;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RichTextViewer({ content, className }: Props) {
  const html = useMemo(() => {
    if (!content) return "";
    const raw = nodeToHtml(content);
    return renderFormulas(raw);
  }, [content]);

  return (
    <div
      className={className}
      // KaTeX CSS is imported globally; we apply minimal prose styles inline
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// ---------------------------------------------------------------------------
// Helper: extract plain text from Tiptap JSON (for previews / CSV export)
// ---------------------------------------------------------------------------

export function tiptapToText(node: any): string {
  if (!node) return "";
  if (node.type === "text") return node.text ?? "";
  return (node.content ?? []).map(tiptapToText).join("");
}
