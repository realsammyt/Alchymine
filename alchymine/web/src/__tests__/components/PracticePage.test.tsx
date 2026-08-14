import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import PracticePage from "@/app/practice/page";
import { LOSS_AVERSION_BANNED } from "@/components/practice/PracticeRhythm";
import type { PracticeSummaryResponse, TodayResponse } from "@/lib/api";

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
  usePathname: jest.fn().mockReturnValue("/practice"),
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "test-user", email: "test@example.com" },
    isLoading: false,
    logout: jest.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

const mockGetToday = jest.fn();
const mockGetSummary = jest.fn();
const mockListPractices = jest.fn();
const mockLogPractice = jest.fn();
const mockCreateIntegration = jest.fn();

jest.mock("@/lib/api", () => ({
  getPracticeToday: (...args: unknown[]) => mockGetToday(...args),
  getPracticeSummary: (...args: unknown[]) => mockGetSummary(...args),
  listPractices: (...args: unknown[]) => mockListPractices(...args),
  logPractice: (...args: unknown[]) => mockLogPractice(...args),
  createIntegration: (...args: unknown[]) => mockCreateIntegration(...args),
}));

const TODAY: TodayResponse = {
  day_key: "2026-08-14",
  generated_at: "2026-08-14T08:00:00+00:00",
  protocol_size: 1,
  items: [
    {
      pack_id: "alchymine-foundations",
      slug: "find-the-floor",
      title: "Find the Floor",
      summary: "Find the parts of you that are already being held up.",
      purpose: "steadiness",
      purposes: ["steadiness"],
      category: "somatic",
      duration_minutes: 5,
      reason: "You have not practiced steadiness this week.",
      reason_template: "balance",
    },
  ],
  slots: {
    morning: [
      {
        pack_id: "alchymine-foundations",
        slug: "find-the-floor",
        prompt: "Morning prompt",
      },
    ],
    day: [
      {
        pack_id: "alchymine-foundations",
        slug: "find-the-floor",
        prompt: "Midday prompt",
      },
    ],
    evening: [
      {
        pack_id: "alchymine-foundations",
        slug: "find-the-floor",
        prompt: "Evening prompt",
      },
    ],
  },
};

const SUMMARY: PracticeSummaryResponse = {
  day_key: "2026-08-14",
  days_practiced_last_7: 4,
  last_7: [true, false, true, false, false, true, true],
  by_purpose: { steadiness: 4 },
  total_completed: 6,
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetToday.mockResolvedValue(TODAY);
  mockGetSummary.mockResolvedValue(SUMMARY);
  mockListPractices.mockResolvedValue([]);
  // 21:45 local on 14 August. Late enough that anywhere east of UTC has
  // already rolled over in UTC terms, which is exactly the case a
  // toISOString()-based day key gets wrong.
  jest.useFakeTimers({ now: new Date(2026, 7, 14, 21, 45).getTime() });
});

afterEach(() => {
  jest.useRealTimers();
});

describe("PracticePage", () => {
  it("sends the user's local day, not the UTC one", async () => {
    render(<PracticePage />);

    await waitFor(() => expect(mockGetToday).toHaveBeenCalled());
    expect(mockGetToday.mock.calls[0][0]).toBe("2026-08-14");
    await waitFor(() => expect(mockGetSummary).toHaveBeenCalled());
    expect(mockGetSummary.mock.calls[0][0]).toBe("2026-08-14");
  });

  it("shows a loading state before the protocol arrives", () => {
    mockGetToday.mockReturnValue(new Promise(() => {}));
    render(<PracticePage />);

    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it("renders the protocol once loaded", async () => {
    render(<PracticePage />);

    // Once per slot: the protocol is N practices rendered three times.
    expect(await screen.findAllByText("Find the Floor")).toHaveLength(3);
  });

  it("renders the rhythm caption", async () => {
    render(<PracticePage />);

    expect(
      await screen.findByText("Practiced 4 of the last 7 days."),
    ).toBeInTheDocument();
  });

  it("shows an error state with a retry when the protocol fails", async () => {
    mockGetToday.mockRejectedValue(new Error("HTTP 500"));
    render(<PracticePage />);

    expect(await screen.findByText(/could not load/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeEnabled();
  });

  it("refetches with refresh when the user asks for a different set", async () => {
    render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    fireEvent.click(screen.getByRole("button", { name: /different practices/i }));

    await waitFor(() =>
      expect(mockGetToday).toHaveBeenCalledWith(
        "2026-08-14",
        expect.objectContaining({ refresh: true }),
      ),
    );
  });

  it("links to the library", async () => {
    render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    expect(
      screen.getByRole("link", { name: /library/i }),
    ).toHaveAttribute("href", "/practice/library");
  });

  it("contains no loss-aversion language", async () => {
    const { container } = render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    // The canonical list, not a copy of part of it. A local subset drifts
    // from the export the moment anything is added to it, which defeats
    // the point of having one list.
    const rendered = container.innerHTML.toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(rendered).not.toContain(banned);
    }
  });
});
