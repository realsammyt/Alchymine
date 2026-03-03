import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/page";

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

// Mock useAuth to return an authenticated user so ProtectedRoute renders children
jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: {
      id: "test-user",
      email: "test@example.com",
      version: "1.0",
      created_at: "2024-01-01",
    },
    isLoading: false,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

describe("DashboardPage", () => {
  it("renders without crashing", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("displays the page description", () => {
    render(<DashboardPage />);
    expect(
      screen.getByText(/Your personal transformation at a glance/),
    ).toBeInTheDocument();
  });

  it("renders all five system cards", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Personalized Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Ethical Healing")).toBeInTheDocument();
    expect(screen.getByText("Generational Wealth")).toBeInTheDocument();
    expect(screen.getByText("Creative Development")).toBeInTheDocument();
    expect(screen.getByText("Perspective Enhancement")).toBeInTheDocument();
  });

  it("has links to all five system pages", () => {
    render(<DashboardPage />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/intelligence");
    expect(hrefs).toContain("/healing");
    expect(hrefs).toContain("/wealth");
    expect(hrefs).toContain("/creative");
    expect(hrefs).toContain("/perspective");
  });

  it('has a "Begin Discovery" link', () => {
    render(<DashboardPage />);
    const discoveryLink = screen.getByText("Begin Discovery");
    expect(discoveryLink).toBeInTheDocument();
    expect(discoveryLink.closest("a")).toHaveAttribute(
      "href",
      "/discover/intake",
    );
  });

  it("displays the ethics-first design notice", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Ethics-First Design")).toBeInTheDocument();
  });

  it("has proper heading structure", () => {
    render(<DashboardPage />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toBeInTheDocument();
    expect(h1).toHaveTextContent("Dashboard");
  });

  it("has accessible section landmarks", () => {
    render(<DashboardPage />);
    // Check for labeled sections
    expect(screen.getByLabelText("Profile summary")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Five transformation systems"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Ethics and transparency"),
    ).toBeInTheDocument();
  });
});
