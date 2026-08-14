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

  it("disables both controls while a write is in flight", () => {
    renderCard({ state: "saving" });

    expect(screen.getByRole("button", { name: /done/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /not today/i })).toBeDisabled();
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
