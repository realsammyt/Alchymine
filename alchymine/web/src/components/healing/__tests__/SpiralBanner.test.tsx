import { render, screen, waitFor } from "@testing-library/react";
import SpiralBanner from "../SpiralBanner";

// ── Mock data ──────────────────────────────────────────────────────

const mockResponse = {
  primary_system: "healing",
  healing_rank: 1,
  healing_score: 100,
  healing_reason:
    "Your health intention aligns directly with the healing system's modalities.",
  healing_entry_action: "Start your personalized healing modality match",
  for_you_today:
    "Your body and mind are ready for renewal. Start with a short breathwork session.",
  recommended_modalities: [
    {
      modality: "breathwork",
      category: "somatic",
      description: "Conscious breathing techniques for nervous system regulation.",
      evidence_level: "strong",
      entry_action: "Start your personalized healing modality match",
    },
    {
      modality: "coherence_meditation",
      category: "contemplative",
      description: "Heart-brain coherence practice with rhythmic breathing.",
      evidence_level: "strong",
      entry_action: "Start your personalized healing modality match",
    },
  ],
  evidence_level: "strong",
  calculation_type: "deterministic",
};

jest.mock("@/lib/api", () => ({
  getHealingSpiralRoute: jest.fn(() => Promise.resolve(mockResponse)),
}));

// ── Tests ──────────────────────────────────────────────────────────

describe("SpiralBanner", () => {
  it("shows loading state initially", () => {
    render(<SpiralBanner intention="health" />);
    expect(screen.getByTestId("spiral-banner-loading")).toBeInTheDocument();
  });

  it("renders spiral banner with recommendation data", async () => {
    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner")).toBeInTheDocument();
    });

    expect(screen.getByText("Your Alchemical Spiral")).toBeInTheDocument();
    expect(
      screen.getByText(/health intention aligns/),
    ).toBeInTheDocument();
  });

  it("displays the healing rank and score", async () => {
    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner")).toBeInTheDocument();
    });

    expect(screen.getByText("#1 of 5")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("displays the For You Today suggestion", async () => {
    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner")).toBeInTheDocument();
    });

    expect(screen.getByText("For You Today")).toBeInTheDocument();
    expect(
      screen.getByText(/body and mind are ready/),
    ).toBeInTheDocument();
  });

  it("renders recommended modalities list", async () => {
    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner")).toBeInTheDocument();
    });

    expect(screen.getByText("Recommended Modalities")).toBeInTheDocument();
    expect(screen.getByText("breathwork")).toBeInTheDocument();
    expect(screen.getByText("coherence meditation")).toBeInTheDocument();
  });

  it("has proper ARIA landmarks", async () => {
    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner")).toBeInTheDocument();
    });

    const section = screen.getByTestId("spiral-banner");
    expect(section.tagName).toBe("SECTION");
    expect(section).toHaveAttribute("aria-labelledby", "spiral-banner-heading");
    expect(
      screen.getByRole("list", { name: /recommended healing modalities/i }),
    ).toBeInTheDocument();
  });

  it("renders error state when API fails", async () => {
    const { getHealingSpiralRoute } = jest.requireMock("@/lib/api");
    getHealingSpiralRoute.mockRejectedValueOnce(new Error("Network error"));

    render(<SpiralBanner intention="health" />);

    await waitFor(() => {
      expect(screen.getByTestId("spiral-banner-error")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Could not load spiral recommendations."),
    ).toBeInTheDocument();
  });
});
