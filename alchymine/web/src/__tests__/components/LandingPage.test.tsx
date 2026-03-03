import { render, screen } from "@testing-library/react";
import LandingPage from "@/app/page";

// Mock next/link
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

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
  usePathname: jest.fn().mockReturnValue("/"),
}));

// Mock useAuth to return no user (guest viewing landing page)
jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: null,
    isLoading: false,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

describe("LandingPage", () => {
  it("renders without crashing", () => {
    render(<LandingPage />);
    expect(screen.getByText("Discover Who You Truly Are")).toBeInTheDocument();
  });

  it("displays the hero tagline", () => {
    render(<LandingPage />);
    expect(
      screen.getByText("Through Five Integrated Systems"),
    ).toBeInTheDocument();
  });

  it("renders all five systems", () => {
    render(<LandingPage />);
    expect(screen.getByText("Personalized Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Ethical Healing")).toBeInTheDocument();
    expect(screen.getByText("Generational Wealth")).toBeInTheDocument();
    expect(screen.getByText("Creative Development")).toBeInTheDocument();
    expect(screen.getByText("Perspective Enhancement")).toBeInTheDocument();
  });

  it("has sign in and get started links in header", () => {
    render(<LandingPage />);
    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByText("Get Started")).toBeInTheDocument();
  });

  it("has links to signup", () => {
    render(<LandingPage />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/signup");
    expect(hrefs).toContain("/login");
  });

  it("renders the How It Works section", () => {
    render(<LandingPage />);
    // "How It Works" appears as both a CTA button and a section heading
    expect(screen.getAllByText("How It Works").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText("Discovery")).toBeInTheDocument();
    expect(screen.getByText("Blueprint")).toBeInTheDocument();
    expect(screen.getByText("Path")).toBeInTheDocument();
  });

  it("renders the trust/ethics section", () => {
    render(<LandingPage />);
    expect(screen.getByText("Built on Trust")).toBeInTheDocument();
    // Trust card titles appear as headings within the ethics section
    expect(screen.getAllByText("Open Source").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Math-Only Finance")).toBeInTheDocument();
    expect(screen.getByText("Local-First Data")).toBeInTheDocument();
    expect(screen.getByText("No Dark Patterns")).toBeInTheDocument();
  });

  it("renders the CTA section with invitation and waitlist cards", () => {
    render(<LandingPage />);
    expect(screen.getByText("Have an Invitation?")).toBeInTheDocument();
    expect(screen.getByText("Join the Waitlist")).toBeInTheDocument();
  });

  it("renders the footer with license info", () => {
    render(<LandingPage />);
    expect(
      screen.getByText("CC-BY-NC-SA 4.0 — The Alchymine Project"),
    ).toBeInTheDocument();
  });
});
