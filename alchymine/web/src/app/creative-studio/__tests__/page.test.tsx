/**
 * Creative Studio: what the user sees when the daily image allowance runs
 * out. Spending the cap is a normal end to a productive session, so it
 * gets its own wait state with a reset time, not the red error banner
 * that means something broke.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import CreativeStudioPage from "../page";
import { ArtUnavailableError, generateArt } from "@/lib/artApi";

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
    identity: null,
    healing: null,
    wealth: null,
    creative: { creative_orientation: "visual" },
    perspective: null,
  }),
}));

jest.mock("@/lib/artApi", () => {
  class MockArtUnavailableError extends Error {
    code: string;
    retryAt: Date | null;
    upgradeUrl: string | null;
    constructor(
      code: string,
      message: string,
      retryAt: Date | null,
      upgradeUrl: string | null = null,
    ) {
      super(message);
      this.name = "ArtUnavailableError";
      this.code = code;
      this.retryAt = retryAt;
      this.upgradeUrl = upgradeUrl;
    }
  }
  // Mirrors the real narrowing: the two plan codes become an upsell with
  // somewhere to click, everything else stays a plain wait state.
  const { PlanGateError } = jest.requireActual("@/lib/planGate");
  return {
    ArtUnavailableError: MockArtUnavailableError,
    asPlanGate: (error: MockArtUnavailableError) =>
      error.code === "plan_upgrade_required" ||
      error.code === "plan_allowance_reached"
        ? new PlanGateError(
            error.code,
            error.message,
            error.retryAt,
            null,
            error.upgradeUrl ?? "/pricing",
          )
        : null,
    generateArt: jest.fn(),
    listGeneratedImages: jest.fn().mockResolvedValue({ images: [] }),
    deleteGeneratedImage: jest.fn(),
    listStylePresets: jest.fn().mockResolvedValue([
      { id: "mystical", name: "Mystical", description: "Sacred geometry" },
    ]),
  };
});

const CAP_MESSAGE =
  "That's all of today's image generations. Your next one unlocks at midnight UTC.";

async function generateWithPrompt(): Promise<void> {
  const textarea = await screen.findByLabelText(/your vision/i);
  fireEvent.change(textarea, { target: { value: "a quiet forest" } });
  fireEvent.click(screen.getByRole("button", { name: /generate/i }));
}

describe("CreativeStudioPage daily cap", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows the cap message rather than a raw error", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByText(new RegExp(CAP_MESSAGE, "i"))).toBeInTheDocument();
    });
    expect(screen.queryByText(/429/)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed/i)).not.toBeInTheDocument();
  });

  it("announces the wait state politely, not as an alert", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/all of today/i);
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the typed prompt so the work is not lost", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
    expect(await screen.findByLabelText(/your vision/i)).toHaveValue(
      "a quiet forest",
    );
  });

  it("shows the same wait state when the global spend breaker trips", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "llm_temporarily_unavailable",
        "This feature is taking a short break while we catch up on demand. Please try again later.",
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/short break/i);
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("still shows a real error banner for genuine failures", async () => {
    (generateArt as jest.Mock).mockRejectedValue(new Error("network down"));

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/network down/i);
    });
  });
});

describe("CreativeStudioPage plan upsell", () => {
  const UPGRADE_MESSAGE =
    "Image generation is part of a paid plan. Upgrade to make yours.";
  const ALLOWANCE_MESSAGE =
    "You've used this month's included images. Upgrade to keep going.";

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("offers an upgrade when the plan does not include art", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError("plan_upgrade_required", UPGRADE_MESSAGE, null, "/pricing"),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/part of a paid plan/i);
    });
    expect(screen.getByRole("link", { name: /see plans/i })).toHaveAttribute(
      "href",
      "/pricing",
    );
    // A sales moment, never a fault.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says when a spent allowance comes back", async () => {
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "plan_allowance_reached",
        ALLOWANCE_MESSAGE,
        new Date("2026-09-01T00:00:00Z"),
        "/pricing",
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByText(/Resets on September 1/)).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: /see plans/i })).toBeInTheDocument();
  });

  it("keeps the daily cap free of an upgrade pitch", async () => {
    // Waiting fixes the daily cap, so selling an upgrade for it would be
    // selling something that changes nothing.
    (generateArt as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<CreativeStudioPage />);
    await generateWithPrompt();

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
    expect(screen.queryByRole("link", { name: /see plans/i })).not.toBeInTheDocument();
  });
});
