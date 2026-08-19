import { render, screen } from "@testing-library/react";
import JourneyChart, { describeJourneyDay, formatShift } from "../JourneyChart";
import type { JourneyDay } from "@/lib/api";

function day(overrides: Partial<JourneyDay> = {}): JourneyDay {
  return {
    day_key: "2026-08-18",
    completed: 0,
    purposes: [],
    loops: 0,
    average_shift: null,
    ...overrides,
  };
}

describe("formatShift", () => {
  it("signs a positive shift so it reads as a direction", () => {
    expect(formatShift(1.5)).toBe("+1.5");
    expect(formatShift(2)).toBe("+2");
  });

  it("keeps a negative shift negative and zero plain", () => {
    expect(formatShift(-1)).toBe("-1");
    expect(formatShift(0)).toBe("0");
  });
});

describe("describeJourneyDay", () => {
  it("says nothing happened when nothing did", () => {
    expect(describeJourneyDay(day({ day_key: "2026-08-18" }))).toBe(
      "Tuesday 18 August: nothing logged.",
    );
  });

  it("names the capacities behind the count", () => {
    const text = describeJourneyDay(
      day({ completed: 1, purposes: ["steadiness"] }),
    );

    expect(text).toBe("Tuesday 18 August: 1 practice completed (Steadiness).");
  });

  it("uses the plural for more than one", () => {
    const text = describeJourneyDay(
      day({ completed: 3, purposes: ["steadiness", "reframing"] }),
    );

    expect(text).toContain("3 practices completed (Steadiness, Reframing)");
  });

  it("carries the loop count and the recorded shift", () => {
    const text = describeJourneyDay(
      day({
        completed: 1,
        purposes: ["expression"],
        loops: 2,
        average_shift: -0.5,
      }),
    );

    expect(text).toContain("2 loops closed");
    expect(text).toContain("recorded shift -0.5");
  });

  it("describes a loop closed on a day with no completion", () => {
    const text = describeJourneyDay(day({ loops: 1, average_shift: 1 }));

    expect(text).toBe("Tuesday 18 August: 1 loop closed, recorded shift +1.");
  });
});

describe("JourneyChart", () => {
  const week: JourneyDay[] = [
    day({ day_key: "2026-08-12" }),
    day({ day_key: "2026-08-13", completed: 1, purposes: ["steadiness"] }),
    day({ day_key: "2026-08-14" }),
    day({
      day_key: "2026-08-15",
      completed: 4,
      purposes: ["expression"],
      loops: 1,
      average_shift: 2,
    }),
    day({ day_key: "2026-08-16" }),
    day({ day_key: "2026-08-17" }),
    day({ day_key: "2026-08-18", completed: 2, purposes: ["reframing"] }),
  ];

  it("renders one column per day, including the empty ones", () => {
    render(<JourneyChart days={week} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(7);
  });

  it("describes every column in text, not only in the drawing", () => {
    render(<JourneyChart days={week} />);

    expect(
      screen.getByText(/Wednesday 12 August: nothing logged\./),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Saturday 15 August: 4 practices completed \(Expression\), 1 loop closed, recorded shift \+2\./,
      ),
    ).toBeInTheDocument();
  });

  it("anchors the axis at both ends of the window", () => {
    render(<JourneyChart days={week} />);

    expect(screen.getByText("12 Aug")).toBeInTheDocument();
    expect(screen.getByText("18 Aug")).toBeInTheDocument();
  });

  it("scrolls the track inside its own box so the page does not", () => {
    const { container } = render(<JourneyChart days={week} />);

    expect(container.querySelector(".overflow-x-auto")).not.toBeNull();
  });

  it("keeps a single practice visible against a much taller day", () => {
    const { container } = render(<JourneyChart days={week} />);
    const bars = Array.from(
      container.querySelectorAll<HTMLElement>("[style*='height']"),
    );

    // One completion against a four-completion day is 25%, which the
    // floor leaves alone; the floor exists for windows where the ratio
    // would round a real day down to nothing.
    expect(bars.some((bar) => bar.style.height === "25%")).toBe(true);
    expect(bars.some((bar) => bar.style.height === "100%")).toBe(true);
  });

  it("draws nothing in the shift band on a day with no loops", () => {
    render(
      <JourneyChart days={[day({ day_key: "2026-08-18", completed: 1 })]} />,
    );

    expect(
      screen.getByText(/Tuesday 18 August: 1 practice completed\./),
    ).toBeInTheDocument();
  });
});
