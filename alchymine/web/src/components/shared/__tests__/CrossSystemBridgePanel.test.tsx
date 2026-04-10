import { render, screen, waitFor } from "@testing-library/react";
import CrossSystemBridgePanel from "../CrossSystemBridgePanel";

// ── Mock data ──────────────────────────────────────────────────────

const mockBridges = [
  {
    id: "XS-01",
    name: "Healing Primes Perspective",
    source_system: "healing",
    target_system: "perspective",
    description:
      "Breathwork and somatic work soften rigid thinking patterns, making Kegan stage transitions more accessible.",
    insight_keys: ["regulation_state", "somatic_readiness"],
  },
  {
    id: "XS-06",
    name: "Healed Expression Flows",
    source_system: "healing",
    target_system: "creative",
    description:
      "Clearing somatic blocks through healing practices removes the psychological censorship that suppresses creative output.",
    insight_keys: ["regulation_state", "inhibition_level"],
  },
];

const mockGetBridges = jest.fn(() => Promise.resolve(mockBridges));

jest.mock("@/lib/api", () => ({
  getBridges: (...args: unknown[]) => mockGetBridges(...args),
}));

// ── Tests ──────────────────────────────────────────────────────────

describe("CrossSystemBridgePanel", () => {
  beforeEach(() => {
    mockGetBridges.mockClear();
    mockGetBridges.mockResolvedValue(mockBridges);
  });

  it("shows loading state initially", () => {
    render(<CrossSystemBridgePanel system="healing" />);
    expect(screen.getByText("Loading cross-system connections...")).toBeInTheDocument();
  });

  it("fetches bridges for the given system", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(mockGetBridges).toHaveBeenCalledWith("healing");
    });
  });

  it("renders bridge cards after loading", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Cross-System Connections")).toBeInTheDocument();
    });

    expect(screen.getByTestId("bridge-card-XS-01")).toBeInTheDocument();
    expect(screen.getByTestId("bridge-card-XS-06")).toBeInTheDocument();
  });

  it("displays bridge name and description", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Healing Primes Perspective")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Breathwork and somatic work soften rigid thinking/),
    ).toBeInTheDocument();
    expect(screen.getByText("Healed Expression Flows")).toBeInTheDocument();
  });

  it("shows source and target system labels on each card", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Healing Primes Perspective")).toBeInTheDocument();
    });

    // Both cards have "Ethical Healing" as source
    const sourceLabels = screen.getAllByText("Ethical Healing");
    expect(sourceLabels.length).toBe(2);

    // Target labels
    expect(screen.getByText("Perspective Prism")).toBeInTheDocument();
    expect(screen.getByText("Creative Forge")).toBeInTheDocument();
  });

  it("renders insight keys as tags", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Healing Primes Perspective")).toBeInTheDocument();
    });

    // "regulation state" appears in both bridge cards
    const regulationTags = screen.getAllByText("regulation state");
    expect(regulationTags.length).toBe(2);
    expect(screen.getByText("somatic readiness")).toBeInTheDocument();
    expect(screen.getByText("inhibition level")).toBeInTheDocument();
  });

  it("renders explore links to target systems", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Healing Primes Perspective")).toBeInTheDocument();
    });

    const links = screen.getAllByRole("link");
    const perspectiveLink = links.find((l) => l.getAttribute("href") === "/perspective");
    const creativeLink = links.find((l) => l.getAttribute("href") === "/creative");

    expect(perspectiveLink).toBeInTheDocument();
    expect(creativeLink).toBeInTheDocument();
  });

  it("shows error state when API fails", async () => {
    mockGetBridges.mockRejectedValueOnce(new Error("Network error"));

    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Could not load data")).toBeInTheDocument();
    });

    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("shows empty state when no bridges returned", async () => {
    mockGetBridges.mockResolvedValueOnce([]);

    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(
        screen.getByText("No cross-system bridges found for this system."),
      ).toBeInTheDocument();
    });
  });

  it("has proper ARIA landmarks", async () => {
    render(<CrossSystemBridgePanel system="healing" />);

    await waitFor(() => {
      expect(screen.getByText("Cross-System Connections")).toBeInTheDocument();
    });

    const section = screen.getByTestId("cross-system-bridges");
    expect(section.tagName).toBe("SECTION");
    expect(section).toHaveAttribute(
      "aria-labelledby",
      "cross-system-bridges-heading",
    );
  });
});
