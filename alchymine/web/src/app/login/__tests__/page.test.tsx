import { render, screen } from "@testing-library/react";
import LoginPage from "../page";

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
    user: null,
    isLoading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock("@/components/shared/Button", () => {
  return function MockButton(props: Record<string, unknown>) {
    return <button {...props} />;
  };
});

jest.mock("@/components/shared/MotionReveal", () => ({
  MotionReveal: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

describe("LoginPage", () => {
  it("renders without crashing", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Welcome Back/,
    );
  });

  it("renders email and password inputs", () => {
    render(<LoginPage />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("has a sign-up link", () => {
    render(<LoginPage />);
    const signUpLink = screen.getByText("Sign up");
    expect(signUpLink.closest("a")).toHaveAttribute("href", "/signup");
  });

  it("has a forgot password link", () => {
    render(<LoginPage />);
    const link = screen.getByText(/Forgot password/);
    expect(link.closest("a")).toHaveAttribute("href", "/forgot-password");
  });
});
