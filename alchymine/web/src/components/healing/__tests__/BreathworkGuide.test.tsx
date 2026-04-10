import { render, screen, fireEvent, act } from "@testing-library/react";
import BreathworkGuide, {
  BreathPattern,
  DEFAULT_PATTERNS,
} from "../BreathworkGuide";

// ── Helpers ──────────────────────────────────────────────────────────

const shortPattern: BreathPattern = {
  name: "Test Pattern",
  description: "A test breath pattern",
  phases: [
    { label: "Inhale", seconds: 1 },
    { label: "Exhale", seconds: 1 },
  ],
  cycles: 1,
};

// ── Tests ────────────────────────────────────────────────────────────

describe("BreathworkGuide", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders idle state with pattern details", () => {
    render(<BreathworkGuide pattern={shortPattern} />);

    expect(screen.getByTestId("breathwork-guide-idle")).toBeInTheDocument();
    expect(screen.getByText("Test Pattern")).toBeInTheDocument();
    expect(screen.getByText("A test breath pattern")).toBeInTheDocument();
    expect(screen.getByText("Inhale 1s")).toBeInTheDocument();
    expect(screen.getByText("Exhale 1s")).toBeInTheDocument();
    expect(screen.getByText("1 cycles")).toBeInTheDocument();
  });

  it("shows Begin and Back buttons in idle state", () => {
    const onExit = jest.fn();
    render(<BreathworkGuide pattern={shortPattern} onExit={onExit} />);

    expect(screen.getByText("Begin")).toBeInTheDocument();
    expect(screen.getByText("Back")).toBeInTheDocument();
  });

  it("transitions to running state on Begin click", () => {
    render(<BreathworkGuide pattern={shortPattern} />);
    fireEvent.click(screen.getByText("Begin"));

    expect(screen.getByTestId("breathwork-guide-running")).toBeInTheDocument();
    expect(screen.getByText("Cycle 1 of 1")).toBeInTheDocument();
  });

  it("displays current phase label while running", () => {
    render(<BreathworkGuide pattern={shortPattern} />);
    fireEvent.click(screen.getByText("Begin"));

    expect(screen.getByText("Inhale")).toBeInTheDocument();
  });

  it("shows End Session button while running", () => {
    render(<BreathworkGuide pattern={shortPattern} />);
    fireEvent.click(screen.getByText("Begin"));

    expect(screen.getByText("End Session")).toBeInTheDocument();
  });

  it("calls onExit when Back is clicked in idle", () => {
    const onExit = jest.fn();
    render(<BreathworkGuide pattern={shortPattern} onExit={onExit} />);
    fireEvent.click(screen.getByText("Back"));

    expect(onExit).toHaveBeenCalledTimes(1);
  });

  it("exports DEFAULT_PATTERNS with known patterns", () => {
    expect(DEFAULT_PATTERNS).toHaveLength(3);
    expect(DEFAULT_PATTERNS.map((p) => p.name)).toContain(
      "Box Breathing (4-4-4-4)",
    );
    expect(DEFAULT_PATTERNS.map((p) => p.name)).toContain(
      "Coherence Breathing",
    );
  });

  it("renders SVG circle elements for the breathing animation", () => {
    render(<BreathworkGuide pattern={shortPattern} />);
    fireEvent.click(screen.getByText("Begin"));

    // The component renders an SVG with circle elements
    const svg = screen.getByTestId("breathwork-guide-running").querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("renders the animated breathing div", () => {
    render(<BreathworkGuide pattern={shortPattern} />);
    fireEvent.click(screen.getByText("Begin"));

    // There should be a timer role element
    const timer = screen.getByRole("timer");
    expect(timer).toBeInTheDocument();
  });
});
