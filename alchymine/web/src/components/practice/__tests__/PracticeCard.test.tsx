import { fireEvent, render, screen } from "@testing-library/react";
import PracticeCard from "../PracticeCard";
import { LOSS_AVERSION_BANNED } from "../PracticeRhythm";
import type { ProtocolItem } from "@/lib/api";

const ITEM: ProtocolItem = {
  pack_id: "alchymine-foundations",
  slug: "find-the-floor",
  title: "Find the Floor",
  summary: "Find the parts of you that are already being held up.",
  purpose: "steadiness",
  purposes: ["steadiness"],
  category: "somatic",
  duration_minutes: 5,
  reason: "You have not practiced steadiness this week.",
  reason_template: "balance",
};

function renderCard(overrides: Partial<React.ComponentProps<typeof PracticeCard>> = {}) {
  const props = {
    item: ITEM,
    prompt: "Where are you being held up right now?",
    state: "idle" as const,
    onComplete: jest.fn(),
    onSkip: jest.fn(),
    ...overrides,
  };
  return { ...render(<PracticeCard {...props} />), props };
}

describe("PracticeCard", () => {
  it("shows the title, summary, prompt and reason", () => {
    renderCard();

    expect(screen.getByText("Find the Floor")).toBeInTheDocument();
    expect(
      screen.getByText("Find the parts of you that are already being held up."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Where are you being held up right now?"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("You have not practiced steadiness this week."),
    ).toBeInTheDocument();
  });

  it("shows a duration chip and a purpose chip", () => {
    renderCard();

    expect(screen.getByText("5 min")).toBeInTheDocument();
    expect(screen.getByText("Steadiness")).toBeInTheDocument();
  });

  it("calls onComplete when the complete control is used", async () => {
    const { props } = renderCard();

    fireEvent.click(screen.getByRole("button", { name: /done/i }));

    expect(props.onComplete).toHaveBeenCalledTimes(1);
  });

  it("calls onSkip from the not-today control", async () => {
    const { props } = renderCard();

    fireEvent.click(screen.getByRole("button", { name: /not today/i }));

    expect(props.onSkip).toHaveBeenCalledTimes(1);
  });

  it("reaches both controls by keyboard alone", () => {
    // Native buttons, in the tab order, each focusable. jsdom does not
    // synthesize the click a focused button produces on Enter or Space,
    // so the activation itself is asserted separately above; what this
    // pins is that nothing here is a div with an onClick.
    const { props } = renderCard();

    const done = screen.getByRole("button", { name: /done/i });
    const notToday = screen.getByRole("button", { name: /not today/i });

    for (const control of [done, notToday]) {
      expect(control.tagName).toBe("BUTTON");
      expect(control).not.toHaveAttribute("tabindex", "-1");
      control.focus();
      expect(control).toHaveFocus();
    }

    fireEvent.click(done);
    fireEvent.click(notToday);
    expect(props.onComplete).toHaveBeenCalledTimes(1);
    expect(props.onSkip).toHaveBeenCalledTimes(1);
  });

  it("gives every control a visible focus ring", () => {
    renderCard();

    for (const control of screen.getAllByRole("button")) {
      expect(control.className).toMatch(/focus-visible:/);
    }
  });

  it("confirms a completion without scoring it", () => {
    renderCard({ state: "completed" });

    expect(screen.getByText("Done today.")).toBeInTheDocument();
  });

  it("acknowledges a skip with no penalty copy", () => {
    const { container } = renderCard({ state: "skipped" });

    expect(screen.getByText("Not today. That's fine.")).toBeInTheDocument();
    const rendered = container.innerHTML.toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(rendered).not.toContain(banned);
    }
  });

  it("marks the optimistic outcome busy until the write lands", () => {
    // The card flips to the outcome immediately, so the honest signal is
    // not a disabled button (there is none any more) but a status region
    // that admits the write has not confirmed yet.
    renderCard({ state: "completed", pending: true });

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  });

  it("drops aria-busy once the write has landed", () => {
    renderCard({ state: "completed", pending: false });

    expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "false");
  });

  it("announces the outcome through the status region", () => {
    // WCAG 4.1.3: the completion has to reach a screen reader, and a
    // plain <p> swapped in silently does not.
    renderCard({ state: "completed" });

    expect(screen.getByRole("status")).toHaveTextContent("Done today.");
  });

  it("announces a skip through the same region", () => {
    renderCard({ state: "skipped" });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Not today. That's fine.",
    );
  });

  it("moves focus onto the outcome when the card settles", () => {
    // WCAG 2.4.3: the button the user was standing on is gone, so focus
    // would otherwise fall to <body>.
    const { rerender, props } = renderCard();
    screen.getByRole("button", { name: /done/i }).focus();

    rerender(<PracticeCard {...props} state="completed" />);

    expect(screen.getByRole("status")).toHaveFocus();
  });

  it("returns focus to the complete control when a write rolls back", () => {
    const { rerender, props } = renderCard({ state: "completed" });

    rerender(
      <PracticeCard
        {...props}
        state="idle"
        error="That didn't save. Have another go in a moment."
      />,
    );

    expect(screen.getByRole("button", { name: /done/i })).toHaveFocus();
  });

  it("does not steal focus on first render", () => {
    renderCard({ state: "completed" });

    expect(document.body).toHaveFocus();
  });

  it("names the card through its heading rather than a duplicate label", () => {
    renderCard();

    const card = screen.getByRole("article", { name: "Find the Floor" });
    expect(card).toBeInTheDocument();
    expect(card).not.toHaveAttribute("aria-label");
  });

  it("shows an inline error and keeps the controls usable", () => {
    renderCard({ state: "idle", error: "Could not save that just now." });

    expect(
      screen.getByText("Could not save that just now."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /done/i })).toBeEnabled();
  });

  it("announces the error politely rather than as an alert", () => {
    renderCard({ error: "Could not save that just now." });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Could not save that just now.",
    );
  });

  it("renders children in the follow-up region", () => {
    renderCard({
      state: "completed",
      children: <p>self check goes here</p>,
    });

    expect(screen.getByText("self check goes here")).toBeInTheDocument();
  });
});
