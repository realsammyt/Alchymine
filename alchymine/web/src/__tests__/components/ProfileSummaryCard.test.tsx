import { render, screen } from "@testing-library/react";
import ProfileSummaryCard from "@/components/shared/ProfileSummaryCard";

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

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "test-user", email: "test@example.com" },
    isLoading: false,
  }),
}));

const mockUseIntake = jest.fn();
jest.mock("@/lib/useApi", () => ({
  useIntake: (...args: unknown[]) => mockUseIntake(...args),
  useApi: jest
    .fn()
    .mockReturnValue({ data: null, loading: false, error: null }),
}));

jest.mock("@/lib/api", () => ({
  getProfile: jest.fn(),
}));

describe("ProfileSummaryCard", () => {
  it("returns null when intake is loading", () => {
    mockUseIntake.mockReturnValue({ data: null, loading: true });
    const { container } = render(<ProfileSummaryCard />);
    expect(container.firstChild).toBeNull();
  });

  it("returns null when no intake data exists", () => {
    mockUseIntake.mockReturnValue({ data: null, loading: false });
    const { container } = render(<ProfileSummaryCard />);
    expect(container.firstChild).toBeNull();
  });

  it("renders user name when intake data exists", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    expect(screen.getByText("Sam Thompson")).toBeInTheDocument();
  });

  it("renders View Full Profile link", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    const link = screen.getByText("View Full Profile →");
    expect(link.closest("a")).toHaveAttribute("href", "/profile");
  });

  it("renders 5 system dots", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    const dots = screen.getAllByTestId(/^system-dot-/);
    expect(dots).toHaveLength(5);
  });
});
