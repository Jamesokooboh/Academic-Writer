"use client";

import { useState } from "react";
import {
  ApiError,
  acceptChange,
  analyzeDocument,
  getMetrics,
  rejectChange,
  rewriteDocument,
  type AnalyzeResult,
  type DocumentMetrics,
  type RewriteRunResult,
  type SentenceOut,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  GOOD: "text-emerald-700 dark:text-emerald-400",
  NEEDS_IMPROVEMENT: "text-amber-700 dark:text-amber-400",
  REWRITTEN: "text-sky-700 dark:text-sky-400",
};

export function PipelinePanel({ documentId }: { documentId: number }) {
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [rewrite, setRewrite] = useState<RewriteRunResult | null>(null);
  const [metrics, setMetrics] = useState<DocumentMetrics | null>(null);
  const [decisions, setDecisions] = useState<Record<number, "accepted" | "rejected">>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setBusy("Analyzing…");
    setError(null);
    try {
      const result = await analyzeDocument(documentId);
      setAnalysis(result);
      setRewrite(null);
      setDecisions({});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Analysis failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleRewrite() {
    setBusy("Rewriting flagged sentences (calls a real LLM)…");
    setError(null);
    try {
      const result = await rewriteDocument(documentId);
      setRewrite(result);
      setMetrics(await getMetrics(documentId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rewrite failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleDecision(sentenceId: number, decision: "accept" | "reject") {
    setBusy(decision === "accept" ? "Accepting…" : "Rejecting…");
    setError(null);
    try {
      if (decision === "accept") await acceptChange(documentId, sentenceId);
      else await rejectChange(documentId, sentenceId);
      setDecisions((prev) => ({ ...prev, [sentenceId]: decision === "accept" ? "accepted" : "rejected" }));
      setMetrics(await getMetrics(documentId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not record decision");
    } finally {
      setBusy(null);
    }
  }

  const sentences: SentenceOut[] = analysis ? analysis.chunks.flatMap((c) => c.sentences) : [];

  return (
    <div className="flex flex-col gap-4 border-t border-black/10 pt-6 dark:border-white/10">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm font-semibold">Rewrite pipeline</h2>
        <button
          onClick={handleAnalyze}
          disabled={!!busy}
          className="rounded border border-black/20 px-2 py-1 text-sm disabled:opacity-50 dark:border-white/20"
        >
          Analyze
        </button>
        {analysis && analysis.needs_improvement_count > 0 && !rewrite && (
          <button
            onClick={handleRewrite}
            disabled={!!busy}
            className="rounded border border-black/20 px-2 py-1 text-sm disabled:opacity-50 dark:border-white/20"
          >
            Rewrite {analysis.needs_improvement_count} flagged sentence
            {analysis.needs_improvement_count === 1 ? "" : "s"}
          </button>
        )}
        {busy && <span className="text-xs text-zinc-500">{busy}</span>}
        {error && <span className="text-xs text-red-600">{error}</span>}
      </div>

      {analysis && (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-zinc-500">
            {analysis.good_count} good · {analysis.needs_improvement_count} flagged for improvement
          </p>
          <ul className="flex flex-col gap-2 rounded border border-black/10 p-4 text-sm dark:border-white/10">
            {sentences.map((s) => (
              <li key={s.id} className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold uppercase ${STATUS_STYLES[s.status]}`}>
                    {s.status.replace("_", " ")}
                  </span>
                  {s.quality_score !== null && (
                    <span className="text-xs text-zinc-500">score {s.quality_score.toFixed(2)}</span>
                  )}
                </div>
                <p>{s.original_text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {rewrite && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-zinc-500">
            {rewrite.results.length} rewrite{rewrite.results.length === 1 ? "" : "s"} passed validation ·{" "}
            {rewrite.total_input_tokens + rewrite.total_output_tokens} tokens · ${rewrite.total_cost_usd.toFixed(4)}
          </p>
          {rewrite.results.length === 0 && (
            <p className="text-xs text-zinc-500">
              No rewrites passed the two-stage validation — flagged sentences kept their original text.
            </p>
          )}
          {rewrite.results.map((r) => (
            <div key={r.sentence_id} className="flex flex-col gap-2 rounded border border-black/10 p-4 dark:border-white/10">
              <div className="text-sm leading-relaxed">
                <span className="text-red-600 line-through decoration-2 dark:text-red-400">{r.original_text}</span>{" "}
                <span className="text-emerald-700 underline decoration-2 dark:text-emerald-400">{r.rewritten_text}</span>
              </div>
              <p className="text-xs text-zinc-500">
                stage A {r.stage_a_score.toFixed(2)}
                {r.stage_b_score !== null && ` · stage B ${r.stage_b_score.toFixed(2)}`}
              </p>
              {decisions[r.sentence_id] ? (
                <span className="text-xs font-semibold uppercase text-zinc-500">{decisions[r.sentence_id]}</span>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDecision(r.sentence_id, "accept")}
                    disabled={!!busy}
                    className="rounded border border-black/20 px-2 py-1 text-xs disabled:opacity-50 dark:border-white/20"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => handleDecision(r.sentence_id, "reject")}
                    disabled={!!busy}
                    className="rounded border border-black/20 px-2 py-1 text-xs disabled:opacity-50 dark:border-white/20"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {metrics && (
        <p className="text-xs text-zinc-500">
          {metrics.good_count} good · {metrics.needs_improvement_count} flagged · {metrics.rewritten_count} rewritten ·{" "}
          {metrics.original_word_count}→{metrics.rewritten_word_count} words · ${metrics.total_cost_usd.toFixed(4)} spent
        </p>
      )}
    </div>
  );
}
