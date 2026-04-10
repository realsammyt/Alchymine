import { render, screen, waitFor } from "@testing-library/react";
import BrandPage from "../page";

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

jest.mock("@/lib/artApi", () => ({
  getBrandPalette: jest.fn().mockResolvedValue({
    primary: { hex: "#C4503A", name: "Ember Red" },
    secondary: { hex: "#E8A33A", name: "Flame Gold" },
    accent: { hex: "#E07A5F", name: "Creator Coral" },
    neutral: { hex: "#2B1D1D", name: "Charcoal" },
  }),
  generateBrandLogo: jest.fn(),
  fetchImageBlobUrl: jest.fn(),
}));

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
