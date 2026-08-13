import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import JourneyPage from "../page";
import { ArtUnavailableError, generateArt } from "@/lib/artApi";
import { getProfile } from "@/lib/api";

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
});

jest.mock("next/navigation", () => ({
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "user-1", email: "test@example.com" },
    isLoading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock("@/lib/api", () => ({
  getProfile: jest.fn().mockResolvedValue({
    id: "user-1",
    version: "2.0",
    intake: { full_name: "Test User" },
    identity: {
      archetype: { primary: "sage" },
      astrology: { sun_sign: "Pisces" },
    },
    healing: null,
    wealth: null,
    creative: null,
    perspective: null,
  }),
  listUserReports: jest.fn().mockResolvedValue({ reports: [], count: 0 }),
}));

jest.mock("@/lib/artApi", () => {
  class MockArtUnavailableError extends Error {
    code: string;
    retryAt: Date | null;
    constructor(code: string, message: string, retryAt: Date | null) {
      super(message);
      this.name = "ArtUnavailableError";
      this.code = code;
      this.retryAt = retryAt;
    }
  }
  return {
    ArtUnavailableError: MockArtUnavailableError,
    listGeneratedImages: jest.fn().mockResolvedValue({ images: [] }),
    generateArt: jest.fn(),
    fetchImageBlobUrl: jest.fn(),
  };
});

describe("JourneyPage", () => {
  it("renders the page heading", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1 }),
      ).toHaveTextContent(/Your Journey/);
    });
  });

  it("renders the progress bar", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });
  });

  it("renders milestone items", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      expect(screen.getByText("Intake")).toBeInTheDocument();
      expect(screen.getByText("Identity")).toBeInTheDocument();
      expect(screen.getByText("Healing")).toBeInTheDocument();
      expect(screen.getByText("Wealth")).toBeInTheDocument();
      expect(screen.getByText("Creative")).toBeInTheDocument();
      expect(screen.getByText("Perspective")).toBeInTheDocument();
      expect(screen.getByText("Synthesis")).toBeInTheDocument();
    });
  });

  it("marks completed milestones", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      // Intake and Identity are completed (mocked profile has them)
      const completeBadges = screen.getAllByText("Complete");
      expect(completeBadges.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("has a back link to dashboard", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      const link = screen.getByText(/Back to Dashboard/);
      expect(link.closest("a")).toHaveAttribute("href", "/dashboard");
    });
  });
});

describe("JourneyPage milestone art cost states", () => {
  const CAP_MESSAGE =
    "That's all of today's image generations. Your next one unlocks at midnight UTC.";

  beforeEach(() => {
    jest.clearAllMocks();
    // A completed milestone is what puts a Generate button on screen.
    (getProfile as jest.Mock).mockResolvedValue({
      id: "user-1",
      version: "2.0",
      intake: { full_name: "Test User" },
      identity: { archetype: { primary: "sage" } },
      healing: { modalities: ["breathwork"] },
      wealth: null,
      creative: null,
      perspective: null,
    });
  });

  async function generateMilestoneArt(): Promise<void> {
    // Several milestones complete from this profile, so several buttons
    // render. Any one of them exercises the same handler.
    const buttons = await screen.findAllByRole("button", {
      name: /generate illustration/i,
    });
    fireEvent.click(buttons[0]);
  }

  it("renders a spent allowance as a wait, not a failure", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<JourneyPage />);
    await generateMilestoneArt();

    await waitFor(() => {
      expect(screen.getByText(new RegExp(CAP_MESSAGE, "i"))).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders a tripped spend breaker the same way", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "llm_temporarily_unavailable",
        "This feature is taking a short break while we catch up on demand. Please try again later.",
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<JourneyPage />);
    await generateMilestoneArt();

    await waitFor(() => {
      expect(screen.getByText(/short break/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("still shows a real error banner for genuine failures", async () => {
    (generateArt as jest.Mock).mockRejectedValue(new Error("network down"));

    render(<JourneyPage />);
    await generateMilestoneArt();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/network down/i);
    });
  });
});
