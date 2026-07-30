import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { REWRITE_STRENGTHS, SettingsPanel, WORD_COUNT_MODES, WRITING_MODES, type EditorSettings } from "./SettingsPanel";

const BASE_SETTINGS: EditorSettings = {
  writingMode: "Professional",
  wordCountMode: "Balanced",
  rewriteStrength: "Very Conservative",
};

describe("SettingsPanel", () => {
  it("renders every writing mode, word count mode, and rewrite strength option", () => {
    render(<SettingsPanel settings={BASE_SETTINGS} onChange={() => {}} />);

    // "Balanced" is a valid option in both Word Count Mode and Rewrite Strength, so
    // options must be checked within their own <select>, not document-wide.
    const writingMode = within(screen.getByRole("combobox", { name: /writing mode/i }));
    for (const mode of WRITING_MODES) {
      expect(writingMode.getByRole("option", { name: mode })).toBeInTheDocument();
    }
    const wordCountMode = within(screen.getByRole("combobox", { name: /word count mode/i }));
    for (const mode of WORD_COUNT_MODES) {
      expect(wordCountMode.getByRole("option", { name: mode })).toBeInTheDocument();
    }
    const rewriteStrength = within(screen.getByRole("combobox", { name: /rewrite strength/i }));
    for (const strength of REWRITE_STRENGTHS) {
      expect(rewriteStrength.getByRole("option", { name: strength })).toBeInTheDocument();
    }
  });

  it("calls onChange with the updated field while preserving the rest", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SettingsPanel settings={BASE_SETTINGS} onChange={onChange} />);

    await user.selectOptions(screen.getByRole("combobox", { name: /writing mode/i }), "PhD");

    expect(onChange).toHaveBeenCalledWith({ ...BASE_SETTINGS, writingMode: "PhD" });
  });

  it("shows the Strict word-count-mode hint", () => {
    render(<SettingsPanel settings={{ ...BASE_SETTINGS, wordCountMode: "Strict" }} onChange={() => {}} />);
    expect(screen.getByText(/±3%/)).toBeInTheDocument();
  });
});
