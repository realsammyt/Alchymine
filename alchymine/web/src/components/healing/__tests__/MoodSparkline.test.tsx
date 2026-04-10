import { render, screen } from "@testing-library/react";
import MoodSparkline from "../MoodSparkline";

// ── Test data ────────────────────────────────────────────────────────

const sampleData = [
  { date: "2026-04-01", score: 5 },
  { date: "2026-04-02", score: 7 },
  { date: "2026-04-03", score: 6 },
  { date: "2026-04-04", score: 8 },
  { date: "2026-04-05", score: 7 },
  { date: "2026-04-06", score: 9 },
];

// ── Tests ────────────────────────────────────────────────────────────

describe("MoodSparkline", () => {
  it("renders the sparkline with data", () => {
    render(<MoodSparkline data={sampleData} />);

    const container = screen.getByTestId("mood-sparkline");
    expect(container).toBeInTheDocument();
  });

  it("renders an SVG element", () => {
    render(<MoodSparkline data={sampleData} />);

    const svg = screen.getByRole("img");
    expect(svg).toBeInTheDocument();
    expect(svg.tagName).toBe("svg");
  });

  it("shows average score", () => {
    // average = (5+7+6+8+7+9)/6 = 7.0
    render(<MoodSparkline data={sampleData} />);

    expect(screen.getByText("avg 7.0")).toBeInTheDocument();
  });

  it("renders empty state when no data is provided", () => {
    render(<MoodSparkline data={[]} />);

    expect(screen.getByTestId("mood-sparkline-empty")).toBeInTheDocument();
    expect(screen.getByText("No mood data")).toBeInTheDocument();
  });

  it("renders empty state for invalid scores", () => {
    render(<MoodSparkline data={[{ date: "2026-04-01", score: 0 }]} />);

    expect(screen.getByTestId("mood-sparkline-empty")).toBeInTheDocument();
  });

  it("displays optional label", () => {
    render(<MoodSparkline data={sampleData} label="14d mood" />);

    expect(screen.getByText("14d mood")).toBeInTheDocument();
  });

  it("uses custom dimensions", () => {
    render(<MoodSparkline data={sampleData} width={200} height={50} />);

    const svg = screen.getByRole("img");
    expect(svg).toHaveAttribute("width", "200");
    expect(svg).toHaveAttribute("height", "50");
  });

  it("renders dots for each data point", () => {
    render(<MoodSparkline data={sampleData} />);

    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    expect(circles).toHaveLength(6);
  });

  it("renders a polyline for the trend line", () => {
    render(<MoodSparkline data={sampleData} />);

    const svg = screen.getByRole("img");
    const polyline = svg.querySelector("polyline");
    expect(polyline).toBeInTheDocument();
    expect(polyline?.getAttribute("stroke")).toBe("#20b2aa");
  });

  it("truncates to last 14 entries", () => {
    const manyEntries = Array.from({ length: 20 }, (_, i) => ({
      date: `2026-04-${String(i + 1).padStart(2, "0")}`,
      score: (i % 10) + 1,
    }));

    render(<MoodSparkline data={manyEntries} />);

    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    expect(circles).toHaveLength(14);
  });

  it("renders a filled area polygon under the line", () => {
    render(<MoodSparkline data={sampleData} />);

    const svg = screen.getByRole("img");
    const polygon = svg.querySelector("polygon");
    expect(polygon).toBeInTheDocument();
  });

  it("uses custom color for stroke", () => {
    render(<MoodSparkline data={sampleData} color="#ff0000" />);

    const svg = screen.getByRole("img");
    const polyline = svg.querySelector("polyline");
    expect(polyline?.getAttribute("stroke")).toBe("#ff0000");
  });

  it("includes accessible aria-label with average", () => {
    render(<MoodSparkline data={sampleData} />);

    const svg = screen.getByRole("img");
    expect(svg.getAttribute("aria-label")).toContain("average 7.0");
  });

  it("renders a single data point without polygon (needs 2+ for area)", () => {
    render(<MoodSparkline data={[{ date: "2026-04-01", score: 5 }]} />);

    const svg = screen.getByRole("img");
    const circles = svg.querySelectorAll("circle");
    expect(circles).toHaveLength(1);

    // polygon requires dots.length > 1
    const polygon = svg.querySelector("polygon");
    expect(polygon).not.toBeInTheDocument();
  });
});
