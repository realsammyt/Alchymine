import { render, screen } from "@testing-library/react";
import ReportPage from "../page";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
  useParams: jest.fn().mockReturnValue({ id: "test-report-123" }),
}));

jest.mock("@/lib/api", () => ({
  getReport: jest.fn().mockResolvedValue({
    id: "test-report-123",
    status: "complete",
    profile_summary: null,
  }),
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

jest.mock("@/components/shared/Card", () => {
  return function MockCard({ children }: { children: React.ReactNode }) {
    return <div>{children}</div>;
  };
});

jest.mock("@/components/shared/Button", () => {
  return function MockButton(props: Record<string, unknown>) {
    return <button {...props} />;
  };
});

jest.mock("react-markdown", () => {
  return function MockMarkdown({ children }: { children: string }) {
    return <>{children}</>;
  };
});

jest.mock("@/components/shared/MotionReveal", () => ({
  MotionReveal: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  MotionStagger: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  MotionStaggerItem: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

describe("ReportPage", () => {
  it("renders loading state initially", () => {
    render(<ReportPage />);
    expect(screen.getByText(/Loading your report/i)).toBeInTheDocument();
  });

  it("renders report header after loading", async () => {
    render(<ReportPage />);
    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
  });

  it("shows 'Report Generated' when identity layer is missing", async () => {
    render(<ReportPage />);
    const text = await screen.findByText(/Report Generated/);
    expect(text).toBeInTheDocument();
  });
});
