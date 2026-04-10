import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SkillDetailDrawer from "../SkillDetailDrawer";

// ── Mock the API module ──────────────────────────────────────────────

const mockSkill = {
  name: "breathwork-box-breathing",
  modality: "breathwork",
  title: "Box Breathing (4-4-4-4)",
  description:
    "A simple, evidence-based breathing pattern used by Navy SEALs.",
  steps: [
    "Sit upright with both feet on the floor.",
    "Exhale fully through pursed lips.",
    "Inhale slowly through the nose for a count of 4.",
  ],
  evidence_rating: "B" as const,
  contraindications: ["severe asthma during an active flare"],
  duration_minutes: 6,
};

jest.mock("@/lib/api", () => ({
  getHealingSkill: jest.fn(() => Promise.resolve(mockSkill)),
}));

// ── Tests ────────────────────────────────────────────────────────────

describe("SkillDetailDrawer", () => {
  const onClose = jest.fn();

  afterEach(() => {
    jest.clearAllMocks();
    document.body.style.overflow = "";
  });

  it("renders hidden (off-screen) when skillName is null", () => {
    render(<SkillDetailDrawer skillName={null} onClose={onClose} />);
    const drawer = screen.getByTestId("skill-detail-drawer");
    expect(drawer).toHaveClass("translate-x-full");
  });

  it("slides in and shows skill data when skillName is provided", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Box Breathing (4-4-4-4)")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/evidence-based breathing pattern/),
    ).toBeInTheDocument();
    expect(screen.getByText("6 min")).toBeInTheDocument();
    expect(screen.getByText("breathwork")).toBeInTheDocument();
    expect(
      screen.getByText("Moderate (Controlled Studies)"),
    ).toBeInTheDocument();
  });

  it("renders all steps as an ordered list", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Sit upright with both feet on the floor.")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Exhale fully through pursed lips."),
    ).toBeInTheDocument();
  });

  it("shows contraindications when present", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(
        screen.getByText("severe asthma during an active flare"),
      ).toBeInTheDocument();
    });
  });

  it("calls onClose when close button is clicked", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Box Breathing (4-4-4-4)")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("drawer-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when backdrop is clicked", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("drawer-backdrop")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("drawer-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on Escape key press", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Box Breathing (4-4-4-4)")).toBeInTheDocument();
    });

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onStartPractice when Start Practice button is clicked", async () => {
    const onStart = jest.fn();
    render(
      <SkillDetailDrawer
        skillName="breathwork-box-breathing"
        onClose={onClose}
        onStartPractice={onStart}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Start Practice")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Start Practice"));
    expect(onStart).toHaveBeenCalledWith(mockSkill);
  });

  it("does not show Start Practice button without onStartPractice prop", async () => {
    render(
      <SkillDetailDrawer skillName="breathwork-box-breathing" onClose={onClose} />,
    );

    await waitFor(() => {
      expect(screen.getByText("Box Breathing (4-4-4-4)")).toBeInTheDocument();
    });

    expect(screen.queryByText("Start Practice")).not.toBeInTheDocument();
  });
});
