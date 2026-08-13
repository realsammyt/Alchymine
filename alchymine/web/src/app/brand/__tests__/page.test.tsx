import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import BrandPage from "../page";
import { ArtUnavailableError, generateBrandLogo } from "@/lib/artApi";

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
      archetype: { primary: "creator" },
      astrology: { sun_sign: "Leo" },
      numerology: { life_path: 3 },
    },
    healing: null,
    wealth: null,
    creative: null,
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
    getBrandPalette: jest.fn().mockResolvedValue({
      primary: { hex: "#C4503A", name: "Ember Red" },
      secondary: { hex: "#E8A33A", name: "Flame Gold" },
      accent: { hex: "#E07A5F", name: "Creator Coral" },
      neutral: { hex: "#2B1D1D", name: "Charcoal" },
    }),
    generateBrandLogo: jest.fn(),
    fetchImageBlobUrl: jest.fn(),
  };
});

describe("BrandPage", () => {
  it("renders the page heading", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1 }),
      ).toHaveTextContent(/Personal Brand/);
    });
  });

  it("renders the colour palette section", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(screen.getByText("Colour Palette")).toBeInTheDocument();
      expect(screen.getByText("Ember Red")).toBeInTheDocument();
      expect(screen.getByText("Flame Gold")).toBeInTheDocument();
    });
  });

  it("renders the typography section", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(screen.getByText("Typography")).toBeInTheDocument();
      // Fire element fonts
      expect(screen.getByText("Playfair Display")).toBeInTheDocument();
    });
  });

  it("renders the pattern language section", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(screen.getByText("Pattern Language")).toBeInTheDocument();
    });
  });

  it("renders the generate logo button", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /generate.*brand logo/i }),
      ).toBeInTheDocument();
    });
  });

  it("has a back link to creative", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      const link = screen.getByText(/Back to Creative Development/);
      expect(link.closest("a")).toHaveAttribute("href", "/creative");
    });
  });

  it("displays hex codes for all colours", async () => {
    render(<BrandPage />);
    await waitFor(() => {
      expect(screen.getByText("#C4503A")).toBeInTheDocument();
      expect(screen.getByText("#E8A33A")).toBeInTheDocument();
    });
  });
});

describe("BrandPage cost states", () => {
  async function generateLogo(): Promise<void> {
    const button = await screen.findByRole("button", { name: /logo/i });
    fireEvent.click(button);
  }

  const CAP_MESSAGE =
    "That's all of today's image generations. Your next one unlocks at midnight UTC.";

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders a spent allowance as a wait, not a failure", async () => {
    (generateBrandLogo as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<BrandPage />);
    await generateLogo();

    await waitFor(() => {
      expect(screen.getByText(new RegExp(CAP_MESSAGE, "i"))).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders a tripped spend breaker the same way", async () => {
    (generateBrandLogo as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "llm_temporarily_unavailable",
        "This feature is taking a short break while we catch up on demand. Please try again later.",
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<BrandPage />);
    await generateLogo();

    await waitFor(() => {
      expect(screen.getByText(/short break/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("never shows a raw status code to the user", async () => {
    (generateBrandLogo as jest.Mock).mockRejectedValue(
      new ArtUnavailableError(
        "daily_art_cap_reached",
        CAP_MESSAGE,
        new Date("2099-01-01T00:00:00Z"),
      ),
    );

    render(<BrandPage />);
    await generateLogo();

    // Scoped to the banner: the palette swatches render hex codes that
    // happen to contain digit runs like "503".
    const banner = await screen.findByText(new RegExp(CAP_MESSAGE, "i"));
    expect(banner.textContent).not.toMatch(/\b(429|503)\b/);
    expect(banner.textContent).not.toMatch(/error|failed/i);
  });

  it("still shows a real error banner for genuine failures", async () => {
    (generateBrandLogo as jest.Mock).mockRejectedValue(new Error("network down"));

    render(<BrandPage />);
    await generateLogo();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/network down/i);
    });
  });
});
