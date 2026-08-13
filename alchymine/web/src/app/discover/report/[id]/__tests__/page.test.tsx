import { fireEvent, render, screen } from "@testing-library/react";
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
  reassessProfile: jest.fn().mockResolvedValue({
    system: "creative",
    status: "complete",
    updated_data: {},
    narrative: null,
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

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "test-user-123", email: "test@example.com" },
    isLoading: false,
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
  }),
}));

jest.mock("@/components/shared/SupplementModal", () => {
  return function MockSupplementModal() {
    return null;
  };
});

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

describe("ReportPage PDF download states", () => {
  const UPGRADE_BODY = {
    detail: {
      code: "plan_upgrade_required",
      message: "Report downloads are part of a paid plan. Upgrade to get the PDF.",
      retry_at: null,
      meter: null,
      plan: "free",
      upgrade_url: "/pricing",
    },
  };

  function fetchReturning(status: number, body: unknown): jest.Mock {
    const res = { status, ok: status >= 200 && status < 300, json: async () => body };
    return jest.fn().mockResolvedValue({
      ...res,
      clone: () => res,
      blob: async () => new Blob(["pdf"]),
    });
  }

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("renders an upsell rather than an alert when the plan cannot download", async () => {
    // The old handler called window.alert, which a screen reader cannot
    // place in the page and which gives the user nowhere to click.
    const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
    global.fetch = fetchReturning(402, UPGRADE_BODY) as unknown as typeof fetch;

    render(<ReportPage />);
    const button = await screen.findByRole("button", { name: /export pdf/i });
    fireEvent.click(button);

    expect(
      await screen.findByText(/Report downloads are part of a paid plan/),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /see plans/i })).toHaveAttribute(
      "href",
      "/pricing",
    );
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it("keeps a real failure as an alert, not an upsell", async () => {
    global.fetch = fetchReturning(404, { detail: "not ready" }) as unknown as typeof fetch;

    render(<ReportPage />);
    fireEvent.click(await screen.findByRole("button", { name: /export pdf/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/not ready yet/i);
    expect(screen.queryByRole("link", { name: /see plans/i })).not.toBeInTheDocument();
  });
});
