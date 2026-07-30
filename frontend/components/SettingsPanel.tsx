"use client";

export const WRITING_MODES = [
  "Professional",
  "MBA",
  "Business Report",
  "Undergraduate",
  "MSc",
  "PhD",
  "Journal Article",
] as const;

export const WORD_COUNT_MODES = ["Strict", "Balanced", "Flexible"] as const;

export const REWRITE_STRENGTHS = ["Very Conservative", "Conservative", "Balanced", "Aggressive"] as const;

export type WritingMode = (typeof WRITING_MODES)[number];
export type WordCountMode = (typeof WORD_COUNT_MODES)[number];
export type RewriteStrength = (typeof REWRITE_STRENGTHS)[number];

export interface EditorSettings {
  writingMode: WritingMode;
  wordCountMode: WordCountMode;
  rewriteStrength: RewriteStrength;
}

const WORD_COUNT_HINTS: Record<WordCountMode, string> = {
  Strict: "±3% — grammar/punctuation-level fixes only",
  Balanced: "±10%",
  Flexible: "Unlimited",
};

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label htmlFor={id} className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {label}
      </label>
      {children}
    </div>
  );
}

export function SettingsPanel({
  settings,
  onChange,
}: {
  settings: EditorSettings;
  onChange: (next: EditorSettings) => void;
}) {
  const selectClass =
    "rounded border border-black/20 bg-transparent px-2 py-1.5 text-sm dark:border-white/20";

  return (
    <div className="grid grid-cols-1 gap-4 rounded border border-black/10 p-4 sm:grid-cols-3 dark:border-white/10">
      <Field id="writing-mode" label="Writing Mode">
        <select
          id="writing-mode"
          className={selectClass}
          value={settings.writingMode}
          onChange={(e) => onChange({ ...settings, writingMode: e.target.value as WritingMode })}
        >
          {WRITING_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>
      </Field>

      <Field id="word-count-mode" label="Word Count Mode">
        <select
          id="word-count-mode"
          className={selectClass}
          value={settings.wordCountMode}
          onChange={(e) => onChange({ ...settings, wordCountMode: e.target.value as WordCountMode })}
        >
          {WORD_COUNT_MODES.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>
        <span className="text-xs text-zinc-500">{WORD_COUNT_HINTS[settings.wordCountMode]}</span>
      </Field>

      <Field id="rewrite-strength" label="Rewrite Strength">
        <select
          id="rewrite-strength"
          className={selectClass}
          value={settings.rewriteStrength}
          onChange={(e) => onChange({ ...settings, rewriteStrength: e.target.value as RewriteStrength })}
        >
          {REWRITE_STRENGTHS.map((strength) => (
            <option key={strength} value={strength}>
              {strength}
            </option>
          ))}
        </select>
      </Field>
    </div>
  );
}
