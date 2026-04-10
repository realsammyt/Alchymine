import { render, screen, waitFor } from "@testing-library/react";
import JourneyPage from "../page";

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

jest.mock("@/lib/artApi", () => ({
  listGeneratedImages: jest.fn().mockResolvedValue({ images: [] }),
  generateArt: jest.fn(),
  fetchImageBlobUrl: jest.fn(),
}));

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
