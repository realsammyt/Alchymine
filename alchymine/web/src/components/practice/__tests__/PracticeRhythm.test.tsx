import { render, screen } from "@testing-library/react";
import PracticeRhythm, { LOSS_AVERSION_BANNED } from "../PracticeRhythm";

const FOUR_OF_SEVEN = [true, false, true, false, false, true, true];
const NONE = [false, false, false, false, false, false, false];

describe("PracticeRhythm", () => {
  it("renders exactly seven markers as a list", () => {
    render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  it("captions the row with the count out of seven", () => {
    render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    expect(
      screen.getByText("Practiced 4 of the last 7 days."),
    ).toBeInTheDocument();
  });

  it("shows the empty state when nothing was logged", () => {
    render(
      <PracticeRhythm dayKey="2026-08-14" last7={NONE} daysPracticed={0} />,
    );

    expect(
      screen.getByText(
        "No practice logged in the last 7 days. Start wherever you are.",
      ),
    ).toBeInTheDocument();
  });

  it("still renders seven markers in the empty state", () => {
    render(
      <PracticeRhythm dayKey="2026-08-14" last7={NONE} daysPracticed={0} />,
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  it("gives every marker a per-day label in its own contents", () => {
    render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    // last_7 is oldest first, so index 6 is dayKey itself. The label
    // lives in a visually-hidden span inside the <li>, not in an
    // aria-label on it: browse-mode readers commonly read the contents.
    expect(
      screen.getByText("Friday 14 August: practiced"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Saturday 8 August: practiced"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sunday 9 August: no practice logged"),
    ).toBeInTheDocument();
  });

  it("puts the label in the list item rather than on it", () => {
    const { container } = render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    for (const item of Array.from(container.querySelectorAll("li"))) {
      expect(item).not.toHaveAttribute("aria-label");
      expect(item.textContent).not.toBe("");
    }
  });

  it("separates practiced from unpractised by more than colour", () => {
    // WCAG 1.4.11: fill alone left the two states at 1.68:1 against each
    // other. Border style is the signal that survives both low contrast
    // and colour vision differences.
    const { container } = render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    const markers = Array.from(
      container.querySelectorAll('[aria-hidden="true"]'),
    );
    const practiced = markers.filter((m) =>
      m.className.includes("border-primary"),
    );
    const unpractised = markers.filter((m) =>
      m.className.includes("border-dashed"),
    );

    expect(practiced).toHaveLength(4);
    expect(unpractised).toHaveLength(3);
  });

  it("hides the visual markers from assistive tech", () => {
    const { container } = render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBe(7);
  });

  it("renders no loss-aversion language", () => {
    const { container } = render(
      <PracticeRhythm
        dayKey="2026-08-14"
        last7={FOUR_OF_SEVEN}
        daysPracticed={4}
      />,
    );

    const rendered = container.innerHTML.toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(rendered).not.toContain(banned);
    }
  });

  it("renders no loss-aversion language in the empty state either", () => {
    const { container } = render(
      <PracticeRhythm dayKey="2026-08-14" last7={NONE} daysPracticed={0} />,
    );

    const rendered = container.innerHTML.toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(rendered).not.toContain(banned);
    }
  });

  it("never shows a counter that resets to zero", () => {
    // A "0" on its own is the shape of a broken streak counter. The
    // empty state is words, not a number.
    const { container } = render(
      <PracticeRhythm dayKey="2026-08-14" last7={NONE} daysPracticed={0} />,
    );

    expect(container.textContent).not.toMatch(/\b0\b/);
  });
});
