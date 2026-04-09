"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Placeholder from "@tiptap/extension-placeholder";
import Image from "@tiptap/extension-image";
import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

interface Props {
  value: any; // Tiptap JSON doc
  onChange: (json: any) => void;
  placeholder?: string;
  onMediaUpload?: (file: File) => Promise<{ id: string; url: string; mime_type: string }>;
}

function ToolBtn({
  active,
  onClick,
  title,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`px-2 py-0.5 text-xs rounded font-medium transition select-none ${
        active ? "bg-amber-500 text-white" : "text-gray-600 hover:bg-gray-200"
      }`}
    >
      {children}
    </button>
  );
}

export default function RichTextEditor({ value, onChange, placeholder, onMediaUpload }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Image.configure({ inline: false, allowBase64: false }),
      Placeholder.configure({ placeholder: placeholder ?? "Type here…" }),
    ],
    content: value || { type: "doc", content: [{ type: "paragraph" }] },
    onUpdate: ({ editor }) => {
      onChange(editor.getJSON());
    },
    editorProps: {
      attributes: {
        class: "p-3 min-h-[90px] text-sm text-gray-800 focus:outline-none prose prose-sm max-w-none",
      },
    },
  });

  // Sync content when value changes externally (e.g. switching edit targets)
  useEffect(() => {
    if (!editor || editor.isDestroyed) return;
    const incoming = JSON.stringify(value);
    const current = JSON.stringify(editor.getJSON());
    if (incoming !== current) {
      editor.commands.setContent(value || { type: "doc", content: [{ type: "paragraph" }] }, false);
    }
  }, [value]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!editor) return null;

  function insertFormula() {
    const formula = prompt("Enter LaTeX formula (e.g. x^2 + y^2 = z^2 or \\frac{a}{b}):");
    if (!formula) return;
    editor?.chain().focus().insertContent(`$${formula}$`).run();
  }

  async function handleImageFile(file: File) {
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file.");
      return;
    }
    try {
      let url: string;
      if (onMediaUpload) {
        const result = await onMediaUpload(file);
        url = `${process.env.NEXT_PUBLIC_API_URL}${result.url}`;
      } else {
        // Default: upload via API
        const form = new FormData();
        form.append("file", file);
        const res = await api.post("/media", form, { headers: { "Content-Type": "multipart/form-data" } });
        url = `${process.env.NEXT_PUBLIC_API_URL}/media/${res.data.id}`;
      }
      editor?.chain().focus().setImage({ src: url, alt: file.name }).run();
    } catch {
      alert("Image upload failed.");
    }
  }

  return (
    <div className="border border-gray-300 rounded-lg overflow-hidden focus-within:ring-2 focus-within:ring-amber-400 focus-within:border-transparent">
      {/* Toolbar */}
      <div className="flex gap-0.5 px-2 py-1 border-b border-gray-200 bg-gray-50 flex-wrap">
        <ToolBtn active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleBold().run()}>
          <strong>B</strong>
        </ToolBtn>
        <ToolBtn active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()}>
          <em>I</em>
        </ToolBtn>
        <ToolBtn active={editor.isActive("underline")} onClick={() => editor.chain().focus().toggleUnderline().run()}>
          <u>U</u>
        </ToolBtn>

        <span className="w-px bg-gray-300 mx-1 self-stretch" />

        <ToolBtn
          active={editor.isActive("heading", { level: 1 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        >
          H1
        </ToolBtn>
        <ToolBtn
          active={editor.isActive("heading", { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          H2
        </ToolBtn>
        <ToolBtn
          active={editor.isActive("heading", { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          H3
        </ToolBtn>

        <span className="w-px bg-gray-300 mx-1 self-stretch" />

        <ToolBtn
          active={editor.isActive("bulletList")}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          • List
        </ToolBtn>
        <ToolBtn
          active={editor.isActive("orderedList")}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          1. List
        </ToolBtn>
        <ToolBtn
          active={editor.isActive("blockquote")}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
        >
          ❝
        </ToolBtn>
        <ToolBtn
          active={editor.isActive("code")}
          onClick={() => editor.chain().focus().toggleCode().run()}
        >
          {"</>"}
        </ToolBtn>

        <span className="w-px bg-gray-300 mx-1 self-stretch" />

        <ToolBtn onClick={insertFormula} title="Insert LaTeX formula">
          ∑ Formula
        </ToolBtn>
        <ToolBtn onClick={() => fileInputRef.current?.click()} title="Insert image">
          🖼 Image
        </ToolBtn>
      </div>

      {/* Hidden file input for image upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleImageFile(file);
          e.target.value = "";
        }}
      />

      {/* Editor content area */}
      <EditorContent editor={editor} />
    </div>
  );
}
