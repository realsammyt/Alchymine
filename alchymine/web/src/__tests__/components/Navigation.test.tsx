import { render, screen, fireEvent } from "@testing-library/react";
import Navigation from "@/components/shared/Navigation";
import { AuthProvider } from "@/lib/AuthContext";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  usePathname: jest.fn().mockReturnValue("/dashboard"),
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

// Mock auth API calls
jest.mock("@/lib/api", () => ({
  loginUser: jest.fn(),
  registerUser: jest.fn(),
  getMe: jest.fn().mockRejectedValue(new Error("No token")),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

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

describe("Navigation", () => {
  it("renders without crashing", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    // Should render the Alchymine brand text (appears in both desktop sidebar and mobile top bar)
    const brandElements = screen.getAllByText("Alchymine");
    expect(brandElements.length).toBeGreaterThan(0);
  });

  it("renders all system navigation links", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    // Each link appears in desktop sidebar, mobile dropdown, and mobile bottom nav
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Intelligence").length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getAllByText("Healing").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Wealth").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Creative").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Perspective").length).toBeGreaterThanOrEqual(1);
  });

  it("contains links to all five system pages", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const links = screen.getAllByRole("link");
    const hrefs = links.map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/dashboard");
    expect(hrefs).toContain("/intelligence");
    expect(hrefs).toContain("/healing");
    expect(hrefs).toContain("/wealth");
    expect(hrefs).toContain("/creative");
    expect(hrefs).toContain("/perspective");
  });

  it("has navigation landmark roles", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const navs = screen.getAllByRole("navigation");
    expect(navs.length).toBeGreaterThanOrEqual(1);
  });

  it("has accessible labels on navigation landmarks", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const navs = screen.getAllByRole("navigation");
    navs.forEach((nav) => {
      expect(nav).toHaveAttribute("aria-label");
    });
  });

  it("has a mobile menu toggle button", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const toggleButton = screen.getByLabelText("Open navigation menu");
    expect(toggleButton).toBeInTheDocument();
  });

  it("toggles mobile menu when button is clicked", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const toggleButton = screen.getByLabelText("Open navigation menu");
    fireEvent.click(toggleButton);
    // After opening, the label should change
    expect(screen.getByLabelText("Close navigation menu")).toBeInTheDocument();
  });

  it("has a sign in link in the desktop sidebar when not authenticated", () => {
    render(
      <AuthProvider>
        <Navigation />
      </AuthProvider>,
    );
    const signInLinks = screen.getAllByText("Sign In");
    expect(signInLinks.length).toBeGreaterThanOrEqual(1);
  });
});
