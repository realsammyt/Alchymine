import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/dashboard/page";
import { useIntake } from "@/lib/useApi";

// The nudge decides for itself whether to appear, and does so under its
// own tests. What the dashboard owns is where it sits, so it is stubbed
// to something always visible and the placement is what gets asserted.
jest.mock("@/components/practice/PracticeNudge", () => {
  return function MockPracticeNudge() {
    return <div data-testid="practice-nudge-mount" />;
  };
});

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
  useIntake: jest.fn().mockReturnValue({ data: null, loading: false }),
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

  it("offers no practice invitation before intake", () => {
    // Nothing has recommended a protocol yet, so there is nothing to
    // return to and the dashboard does not mount the nudge at all.
    render(<DashboardPage />);
    expect(screen.queryByTestId("practice-nudge-mount")).not.toBeInTheDocument();
  });
});

describe("DashboardPage practice nudge placement", () => {
  beforeEach(() => {
    jest
      .mocked(useIntake)
      .mockReturnValue({ data: { fullName: "Test User" }, loading: false });
  });

  it("mounts the practice nudge once intake is done", () => {
    render(<DashboardPage />);
    expect(screen.getByTestId("practice-nudge-mount")).toBeInTheDocument();
  });

  it("puts it above the tabs, so it survives switching tab", () => {
    render(<DashboardPage />);

    const nudge = screen.getByTestId("practice-nudge-mount");
    const tabs = screen.getByRole("tablist");

    expect(
      nudge.compareDocumentPosition(tabs) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("keeps the page heading first", () => {
    render(<DashboardPage />);

    const heading = screen.getByRole("heading", { level: 1 });
    const nudge = screen.getByTestId("practice-nudge-mount");

    expect(
      heading.compareDocumentPosition(nudge) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
