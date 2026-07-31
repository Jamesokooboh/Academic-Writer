"use client";

import { useEffect, useRef, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { PipelinePanel } from "@/components/PipelinePanel";
import { SettingsPanel, type EditorSettings } from "@/components/SettingsPanel";
import { TrackChanges } from "@/components/TrackChanges";
import { ApiError, createDocument, exportDocument, importDocument, type ExportFormat } from "@/lib/api";

const CONTENT_KEY = "academic_writer_draft_content";
const SETTINGS_KEY = "academic_writer_draft_settings";
const TITLE_KEY = "academic_writer_draft_title";
const DOCUMENT_ID_KEY = "academic_writer_document_id";

const DEFAULT_SETTINGS: EditorSettings = {
  writingMode: "Professional",
  wordCountMode: "Balanced",
  rewriteStrength: "Very Conservative",
};

function toApiSettings(settings: EditorSettings, title: string) {
  return {
    title,
    writing_mode: settings.writingMode,
    word_count_mode: settings.wordCountMode,
    rewrite_strength: settings.rewriteStrength,
  };
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function EditorPageContent() {
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("Untitled");
  const [settings, setSettings] = useState<EditorSettings>(DEFAULT_SETTINGS);
  const [revised, setRevised] = useState("");
  const [documentId, setDocumentId] = useState<number | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is unavailable during SSR; deferring to an effect avoids a hydration mismatch.
    setContent(window.localStorage.getItem(CONTENT_KEY) ?? "");
    setTitle(window.localStorage.getItem(TITLE_KEY) ?? "Untitled");
    const storedId = window.localStorage.getItem(DOCUMENT_ID_KEY);
    if (storedId) setDocumentId(Number(storedId));
    const storedSettings = window.localStorage.getItem(SETTINGS_KEY);
    if (storedSettings) {
      try {
        setSettings(JSON.parse(storedSettings));
      } catch {
        // ignore corrupt local draft
      }
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(CONTENT_KEY, content);
  }, [content]);

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    window.localStorage.setItem(TITLE_KEY, title);
  }, [title]);

  useEffect(() => {
    if (documentId !== null) window.localStorage.setItem(DOCUMENT_ID_KEY, String(documentId));
  }, [documentId]);

  async function handleImportFile(file: File) {
    setBusy("Importing…");
    setError(null);
    try {
      const imported = await importDocument(file, {
        writing_mode: settings.writingMode,
        word_count_mode: settings.wordCountMode,
        rewrite_strength: settings.rewriteStrength,
      });
      setContent(imported.content);
      setTitle(imported.title);
      setDocumentId(imported.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Import failed");
    } finally {
      setBusy(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleCreateDocument() {
    setBusy("Saving…");
    setError(null);
    try {
      const created = await createDocument({ ...toApiSettings(settings, title), content });
      setDocumentId(created.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save document");
    } finally {
      setBusy(null);
    }
  }

  async function handleExport(format: ExportFormat) {
    if (documentId === null) return;
    setBusy(`Exporting .${format}…`);
    setError(null);
    try {
      const blob = await exportDocument(documentId, format);
      downloadBlob(blob, `${title}.${format}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex flex-wrap items-center gap-3 border-b border-black/10 pb-4 dark:border-white/10">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="rounded border border-black/20 bg-transparent px-2 py-1 text-sm font-medium dark:border-white/20"
          aria-label="Document title"
        />

        <input
          ref={fileInputRef}
          type="file"
          accept=".docx,.pdf,.md,.markdown,.txt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleImportFile(file);
          }}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={!!busy}
          className="rounded border border-black/20 px-2 py-1 text-sm disabled:opacity-50 dark:border-white/20"
        >
          Import (.docx/.pdf/.md)
        </button>

        {documentId === null ? (
          <button
            onClick={handleCreateDocument}
            disabled={!!busy || !content.trim()}
            className="rounded border border-black/20 px-2 py-1 text-sm disabled:opacity-50 dark:border-white/20"
          >
            Save to server
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Export:</span>
            {(["md", "docx", "pdf"] as const).map((format) => (
              <button
                key={format}
                onClick={() => handleExport(format)}
                disabled={!!busy}
                className="rounded border border-black/20 px-2 py-1 text-sm uppercase disabled:opacity-50 dark:border-white/20"
              >
                {format}
              </button>
            ))}
          </div>
        )}

        {busy && <span className="text-xs text-zinc-500">{busy}</span>}
        {error && <span className="text-xs text-red-600">{error}</span>}
      </div>

      <SettingsPanel settings={settings} onChange={setSettings} />

      <div className="flex flex-col gap-2">
        <label htmlFor="content" className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Document
        </label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste or write your academic text here…"
          className="min-h-96 w-full resize-y rounded border border-black/20 bg-transparent p-4 font-sans text-sm leading-relaxed dark:border-white/20"
        />
        <p className="text-xs text-zinc-500">
          {content.trim() ? content.trim().split(/\s+/).length : 0} words · autosaved locally
          {documentId !== null && ` · document #${documentId}`}
        </p>
      </div>

      {documentId !== null && <PipelinePanel documentId={documentId} />}

      <div className="flex flex-col gap-2 border-t border-black/10 pt-6 dark:border-white/10">
        <h2 className="text-sm font-semibold">Track Changes diff viewer</h2>
        <p className="text-xs text-zinc-500">
          Paste any original/revised pair here to preview word-level diffing, color-coding, and
          per-change accept/reject — the same component the rewrite pipeline above uses.
        </p>
        <textarea
          value={revised}
          onChange={(e) => setRevised(e.target.value)}
          placeholder="Start from the document text above, then edit here to preview a diff…"
          className="min-h-32 w-full resize-y rounded border border-black/20 bg-transparent p-4 font-sans text-sm leading-relaxed dark:border-white/20"
        />
        {revised && <TrackChanges original={content} revised={revised} />}
      </div>
    </div>
  );
}

export default function EditorPage() {
  return (
    <AuthGuard>
      <EditorPageContent />
    </AuthGuard>
  );
}
