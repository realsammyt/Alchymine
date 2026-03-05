import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/dashboard/page";

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
  usePathname: jest.fn().mockReturnValue("/dashboard"),
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

// Mock useApi to return loading state (no data)
jest.mock("@/lib/useApi", () => ({
  useApi: jest.fn().mockReturnValue({
    data: null,
    loading: false,
    error: new Error("No data"),
  }),
  getStoredIntake: jest.fn().mockReturnValue(null),
}));

describe("DashboardPage", () => {
  it("renders without crashing", () => {
    render(<DashboardPage />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("displays no-intake message when intake is missing", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Welcome to Alchymine")).toBeInTheDocument();
  });

  it("has a call-to-action to start the journey", () => {
    render(<DashboardPage />);
    const link = screen.getByText("Start Your Journey");
    expect(link).toBeInTheDocument();
  });

  it("has a link to the intake page", () => {
    render(<DashboardPage />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/discover/intake");
  });

  it("has proper heading structure", () => {
    render(<DashboardPage />);
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toBeInTheDocument();
    expect(h1).toHaveTextContent(/Welcome/);
  });
});
