import { render, screen } from "@testing-library/react";
import EvidenceRatingBadge from "@/components/shared/EvidenceRatingBadge";

describe("EvidenceRatingBadge", () => {
  it("renders without crashing", () => {
    render(<EvidenceRatingBadge level="strong" />);
    expect(screen.getByText("Peer-Reviewed")).toBeInTheDocument();
  });

  it("renders the correct label for each evidence level", () => {
    const levels = [
      { level: "strong" as const, label: "Peer-Reviewed" },
      { level: "moderate" as const, label: "Emerging Research" },
      { level: "emerging" as const, label: "Theoretical" },
      { level: "traditional" as const, label: "Cultural/Historical" },
      { level: "entertainment" as const, label: "Entertainment" },
    ];

    levels.forEach(({ level, label }) => {
      const { unmount } = render(<EvidenceRatingBadge level={level} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    });
  });

  it("has correct aria-label for accessibility", () => {
    render(<EvidenceRatingBadge level="moderate" />);
    const badge = screen.getByRole("img");
    expect(badge).toHaveAttribute("aria-label");
    expect(badge.getAttribute("aria-label")).toContain("Emerging Research");
  });

  it("renders four evidence dots", () => {
    const { container } = render(<EvidenceRatingBadge level="strong" />);
    const dots = container.querySelectorAll("span > span > span");
    expect(dots).toHaveLength(4);
  });

  it("shows filled dots proportional to evidence level", () => {
    const { container } = render(<EvidenceRatingBadge level="emerging" />);
    const dots = container.querySelectorAll("span > span > span");
    // "emerging" has dotCount=2, so first 2 should be filled (bg-current) and last 2 dimmed (bg-current/20)
    const dotClassNames = Array.from(dots).map((d) => d.className);
    expect(dotClassNames.filter((c) => !c.includes("/20"))).toHaveLength(2);
    expect(dotClassNames.filter((c) => c.includes("/20"))).toHaveLength(2);
  });

  it("shows no filled dots for entertainment level", () => {
    const { container } = render(<EvidenceRatingBadge level="entertainment" />);
    const dots = container.querySelectorAll("span > span > span");
    const dotClassNames = Array.from(dots).map((d) => d.className);
    expect(dotClassNames.filter((c) => c.includes("/20"))).toHaveLength(4);
  });

  it("shows tooltip text by default", () => {
    render(<EvidenceRatingBadge level="traditional" />);
    const badge = screen.getByRole("img");
    expect(badge).toHaveAttribute("title");
    expect(badge.getAttribute("title")).toContain(
      "historical and cultural traditions",
    );
  });

  it("hides tooltip when showTooltip is false", () => {
    render(<EvidenceRatingBadge level="traditional" showTooltip={false} />);
    const badge = screen.getByRole("img");
    expect(badge).not.toHaveAttribute("title");
  });
});
