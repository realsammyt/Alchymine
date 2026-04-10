/**
 * SystemCoachBanner -- component tests.
 *
 * Verifies that each system key renders the correct label, prompt chips,
 * and link targets.
 */

import { render, screen } from "@testing-library/react";

import SystemCoachBanner from "@/components/chat/SystemCoachBanner";

describe("SystemCoachBanner", () => {
  it("renders the healing coach banner with correct label and prompts", () => {
    render(<SystemCoachBanner systemKey="healing" />);

    expect(
      screen.getByText(/talk to your ethical healing coach/i),
    ).toBeInTheDocument();
    // Should render up to 3 starter prompt chips.
    expect(screen.getByText("Breathwork for me")).toBeInTheDocument();
    expect(screen.getByText("My healing journey")).toBeInTheDocument();
    expect(screen.getByText("Shadow work guide")).toBeInTheDocument();
  });

  it("renders the intelligence coach banner with correct label", () => {
    render(<SystemCoachBanner systemKey="intelligence" />);

    expect(
      screen.getByText(/talk to your personal intelligence coach/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Explain my profile")).toBeInTheDocument();
  });

  it("links prompt chips to /chat with system and prompt query params", () => {
    render(<SystemCoachBanner systemKey="wealth" />);

    const chip = screen.getByText("Budget approach");
    expect(chip.closest("a")).toHaveAttribute(
      "href",
      expect.stringContaining("/chat?system=wealth&prompt="),
    );
  });

  it("links the open-chat button to /chat with system param", () => {
    render(<SystemCoachBanner systemKey="creative" />);

    const link = screen.getByText("Open chat").closest("a");
    expect(link).toHaveAttribute("href", "/chat?system=creative");
  });

  it("has the correct data-testid for page-level testing", () => {
    render(<SystemCoachBanner systemKey="perspective" />);

    expect(screen.getByTestId("system-coach-banner")).toBeInTheDocument();
  });
});
