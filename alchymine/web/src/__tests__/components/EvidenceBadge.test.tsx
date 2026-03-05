import { render, screen } from "@testing-library/react";
import EvidenceBadge from "@/components/shared/EvidenceBadge";

describe("EvidenceBadge", () => {
  it("renders the strong level as Peer-Reviewed", () => {
    render(<EvidenceBadge level="strong" />);
    expect(screen.getByText("Peer-Reviewed")).toBeInTheDocument();
  });

  it("renders the moderate level as Emerging Research", () => {
    render(<EvidenceBadge level="moderate" />);
    expect(screen.getByText("Emerging Research")).toBeInTheDocument();
  });

  it("renders the emerging level as Theoretical", () => {
    render(<EvidenceBadge level="emerging" />);
    expect(screen.getByText("Theoretical")).toBeInTheDocument();
  });

  it("renders the traditional level as Cultural/Historical", () => {
    render(<EvidenceBadge level="traditional" />);
    expect(screen.getByText("Cultural/Historical")).toBeInTheDocument();
  });

  it("renders the entertainment level as Entertainment", () => {
    render(<EvidenceBadge level="entertainment" />);
    expect(screen.getByText("Entertainment")).toBeInTheDocument();
  });

  it("is accessible with role=img and aria-label", () => {
    render(<EvidenceBadge level="strong" />);
    const badge = screen.getByRole("img");
    expect(badge).toHaveAttribute("aria-label");
    expect(badge.getAttribute("aria-label")).toContain("Peer-Reviewed");
  });

  it("shows tooltip title by default", () => {
    render(<EvidenceBadge level="strong" />);
    const badge = screen.getByRole("img");
    expect(badge).toHaveAttribute("title");
  });

  it("hides tooltip when showTooltip=false", () => {
    render(<EvidenceBadge level="strong" showTooltip={false} />);
    const badge = screen.getByRole("img");
    expect(badge).not.toHaveAttribute("title");
  });
});
