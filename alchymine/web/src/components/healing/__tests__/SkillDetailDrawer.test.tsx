import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SkillDetailDrawer from "../SkillDetailDrawer";
import { getHealingSkill } from "@/lib/api";
import type { HealingSkill } from "@/lib/api";

// ── Mock the API module ──────────────────────────────────────────────

// Typed as HealingSkill on purpose: this fixture is the round-trip
// check that the interface matches what the endpoint actually sends.
// The four licensing fields are part of that payload, so leaving one
// out here is a compile error rather than a surprise at runtime.
const mockSkill: HealingSkill = {
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
  license: "CC-BY-NC-SA-4.0",
  attribution: "Alchymine Contributors",
  source_url: null,
  bundled: true,
};

/** A skill mounted from outside the repo, under terms Alchymine does not own. */
const externalSkill: HealingSkill = {
  ...mockSkill,
  name: "somatic-borrowed-practice",
  title: "Borrowed Practice",
  license: "CC-BY-4.0",
  attribution: "Someone Else",
  source_url: "https://example.org/skills/borrowed",
  bundled: false,
};

jest.mock("@/lib/api", () => ({
  getHealingSkill: jest.fn(() => Promise.resolve(mockSkill)),
}));

/** Renders the drawer with one payload and waits for it to land. */
async function openWith(skill: HealingSkill) {
  (getHealingSkill as jest.Mock).mockResolvedValue(skill);
  render(<SkillDetailDrawer skillName={skill.name} onClose={jest.fn()} />);
  await waitFor(() => {
    expect(screen.getByText(skill.title)).toBeInTheDocument();
  });
}

// ── Tests ────────────────────────────────────────────────────────────

describe("SkillDetailDrawer", () => {
  const onClose = jest.fn();

  beforeEach(() => {
    // Restored every test because mockResolvedValue outlives
    // clearAllMocks, and a leaked payload is a confusing failure.
    (getHealingSkill as jest.Mock).mockResolvedValue(mockSkill);
  });

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

// ── Attribution ──────────────────────────────────────────────────────

describe("SkillDetailDrawer attribution", () => {
  beforeEach(() => {
    (getHealingSkill as jest.Mock).mockResolvedValue(mockSkill);
  });

  afterEach(() => {
    jest.clearAllMocks();
    document.body.style.overflow = "";
  });

  it("surfaces the license and who wrote it", async () => {
    await openWith(externalSkill);

    expect(screen.getByText(/CC-BY-4.0/)).toBeInTheDocument();
    expect(screen.getByText(/Someone Else/)).toBeInTheDocument();
  });

  it("links the source in a new tab, and says so", async () => {
    await openWith(externalSkill);

    const link = screen.getByRole("link", { name: /source/i });
    expect(link).toHaveAttribute("href", "https://example.org/skills/borrowed");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveTextContent("Source (opens in a new tab)");
  });

  it("omits the link, and its separator, when there is no source url", async () => {
    await openWith(mockSkill);

    expect(
      screen.queryByRole("link", { name: /source/i }),
    ).not.toBeInTheDocument();
    // Exact match: a trailing separator would show up here as the
    // dangling middle dot it is.
    expect(screen.getByTestId("skill-attribution")).toHaveTextContent(
      /^Alchymine Contributors · CC-BY-NC-SA-4\.0$/,
    );
  });

  it("shows license and attribution for a bundled skill too", async () => {
    await openWith(mockSkill);

    expect(screen.getByText(/CC-BY-NC-SA-4.0/)).toBeInTheDocument();
    expect(screen.getByText(/Alchymine Contributors/)).toBeInTheDocument();
  });

  it("keeps the attribution text above the 3:1 contrast floor", async () => {
    await openWith(externalSkill);

    // text-text/60 computes 6.55:1 on this surface, with room to spare
    // over the 4.5:1 WCAG 1.4.3 asks for normal text. /40 would be
    // 3.46:1 and fail it, so the opacity is pinned here.
    expect(screen.getByTestId("skill-attribution").className).toContain(
      "text-text/60",
    );
  });

  it("wraps a long attribution rather than scrolling the drawer", async () => {
    await openWith({
      ...externalSkill,
      attribution: "Averyveryverylongsingletokenattributionwithnospacesatall",
    });

    expect(screen.getByTestId("skill-attribution").className).toContain(
      "break-words",
    );
  });
});
