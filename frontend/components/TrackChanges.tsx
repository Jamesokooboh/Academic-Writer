"use client";

import { useMemo, useState } from "react";
import DiffMatchPatch from "diff-match-patch";

type SegmentType = "equal" | "added" | "removed" | "modified";

interface Segment {
  id: number;
  type: SegmentType;
  text?: string;
  removedText?: string;
  addedText?: string;
}

function buildSegments(original: string, revised: string): Segment[] {
  const dmp = new DiffMatchPatch();
  const diffs = dmp.diff_main(original, revised);
  dmp.diff_cleanupSemantic(diffs);

  const segments: Segment[] = [];
  let id = 0;
  let i = 0;
  while (i < diffs.length) {
    const [op, text] = diffs[i];
    if (op === 0) {
      segments.push({ id: id++, type: "equal", text });
      i++;
    } else if (op === -1) {
      const next = diffs[i + 1];
      if (next && next[0] === 1) {
        segments.push({ id: id++, type: "modified", removedText: text, addedText: next[1] });
        i += 2;
      } else {
        segments.push({ id: id++, type: "removed", removedText: text });
        i++;
      }
    } else {
      segments.push({ id: id++, type: "added", addedText: text });
      i++;
    }
  }
  return segments;
}

export function TrackChanges({ original, revised }: { original: string; revised: string }) {
  const segments = useMemo(() => buildSegments(original, revised), [original, revised]);
  const [accepted, setAccepted] = useState<Record<number, boolean>>({});

  function isAccepted(id: number): boolean {
    return accepted[id] ?? true;
  }

  function setSegmentAccepted(id: number, value: boolean) {
    setAccepted((prev) => ({ ...prev, [id]: value }));
  }

  const finalText = segments
    .map((seg) => {
      if (seg.type === "equal") return seg.text;
      const acceptedChange = isAccepted(seg.id);
      if (seg.type === "added") return acceptedChange ? seg.addedText : "";
      if (seg.type === "removed") return acceptedChange ? "" : seg.removedText;
      return acceptedChange ? seg.addedText : seg.removedText;
    })
    .join("");

  return (
    <div className="space-y-4">
      <div className="rounded border border-black/10 p-4 text-sm leading-relaxed dark:border-white/10">
        {segments.map((seg) => {
          if (seg.type === "equal") {
            return <span key={seg.id}>{seg.text}</span>;
          }

          const acceptedChange = isAccepted(seg.id);

          return (
            <span key={seg.id} className="inline">
              {seg.type !== "added" && (
                <span
                  className={
                    acceptedChange
                      ? "text-red-600 line-through decoration-2 dark:text-red-400"
                      : "text-zinc-700 dark:text-zinc-300"
                  }
                >
                  {seg.removedText}
                </span>
              )}
              {seg.type !== "removed" && (
                <span
                  className={
                    acceptedChange
                      ? "text-emerald-700 underline decoration-2 dark:text-emerald-400"
                      : "hidden"
                  }
                >
                  {seg.addedText}
                </span>
              )}
              <button
                onClick={() => setSegmentAccepted(seg.id, true)}
                disabled={acceptedChange}
                className="mx-0.5 rounded border border-black/20 px-1 text-xs disabled:opacity-30 dark:border-white/20"
                aria-label="Accept change"
              >
                ✓
              </button>
              <button
                onClick={() => setSegmentAccepted(seg.id, false)}
                disabled={!acceptedChange}
                className="mx-0.5 rounded border border-black/20 px-1 text-xs disabled:opacity-30 dark:border-white/20"
                aria-label="Reject change"
              >
                ✗
              </button>
            </span>
          );
        })}
      </div>

      <div>
        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          Result after applying accepted changes
        </h3>
        <p className="rounded border border-black/10 p-4 text-sm leading-relaxed dark:border-white/10">
          {finalText || <span className="text-zinc-500">(empty)</span>}
        </p>
      </div>
    </div>
  );
}
