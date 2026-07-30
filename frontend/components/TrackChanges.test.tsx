import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TrackChanges } from "./TrackChanges";

describe("TrackChanges", () => {
  it("shows the fully-revised text as the default merged result", () => {
    render(<TrackChanges original="The data was analyzed." revised="We analyzed the data." />);

    const result = screen.getByText(/result after applying accepted changes/i).nextElementSibling;
    expect(result?.textContent?.replace(/\s+/g, " ").trim()).toBe("We analyzed the data.");
  });

  it("reverts a single change back to the original text when rejected", () => {
    render(<TrackChanges original="Hello world." revised="Hello there." />);

    const rejectButtons = screen.getAllByRole("button", { name: /reject change/i });
    fireEvent.click(rejectButtons[0]);

    const result = screen.getByText(/result after applying accepted changes/i).nextElementSibling;
    expect(result?.textContent?.replace(/\s+/g, " ").trim()).toBe("Hello world.");
  });

  it("re-accepting after a reject restores the revised text", () => {
    render(<TrackChanges original="Hello world." revised="Hello there." />);

    const rejectButtons = screen.getAllByRole("button", { name: /reject change/i });
    fireEvent.click(rejectButtons[0]);
    const acceptButtons = screen.getAllByRole("button", { name: /accept change/i });
    fireEvent.click(acceptButtons[0]);

    const result = screen.getByText(/result after applying accepted changes/i).nextElementSibling;
    expect(result?.textContent?.replace(/\s+/g, " ").trim()).toBe("Hello there.");
  });

  it("renders unchanged text with no accept/reject controls needed", () => {
    render(<TrackChanges original="Same sentence." revised="Same sentence." />);
    expect(screen.queryAllByRole("button", { name: /accept change|reject change/i })).toHaveLength(0);
  });
});
