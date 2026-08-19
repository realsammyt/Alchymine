import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import PracticePage from "@/app/practice/page";
import { LOSS_AVERSION_BANNED } from "@/components/practice/PracticeRhythm";
import type {
  PracticeLogEntry,
  PracticeLogListResponse,
  PracticeSummaryResponse,
  TodayResponse,
} from "@/lib/api";

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
const mockListPracticeLog = jest.fn();
const mockLogPractice = jest.fn();
const mockCreateIntegration = jest.fn();

// The routes the page calls are stubbed; everything else stays real, so
// a value the page's tree imports for its own use (`ApiError`, which
// DailyProtocol narrows a refused save on) is the real one.
jest.mock("@/lib/api", () => ({
  ...jest.requireActual("@/lib/api"),
  getPracticeToday: (...args: unknown[]) => mockGetToday(...args),
  getPracticeSummary: (...args: unknown[]) => mockGetSummary(...args),
  listPractices: (...args: unknown[]) => mockListPractices(...args),
  listPracticeLog: (...args: unknown[]) => mockListPracticeLog(...args),
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

function logEntry(overrides: Partial<PracticeLogEntry> = {}): PracticeLogEntry {
  return {
    id: "log-1",
    user_id: "test-user",
    pack_id: "alchymine-foundations",
    practice_slug: "find-the-floor",
    primary_purpose: "steadiness",
    purposes: ["steadiness"],
    category: "somatic",
    status: "completed",
    protocol_slot: "morning",
    duration_minutes: null,
    occurred_at: "2026-08-14T08:05:00+00:00",
    day_key: "2026-08-14",
    created_at: "2026-08-14T08:05:00+00:00",
    reflection: null,
    self_check_response: null,
    ...overrides,
  };
}

function logPage(
  entries: PracticeLogEntry[],
  overrides: Partial<PracticeLogListResponse> = {},
): PracticeLogListResponse {
  return {
    entries,
    total: entries.length,
    page: 1,
    per_page: 100,
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetToday.mockResolvedValue(TODAY);
  mockGetSummary.mockResolvedValue(SUMMARY);
  mockListPractices.mockResolvedValue([]);
  mockListPracticeLog.mockResolvedValue(logPage([]));
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
    mockListPracticeLog.mockReturnValue(new Promise(() => {}));
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

  it("offers the practice coach", async () => {
    render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    const banner = screen.getByTestId("system-coach-banner");
    expect(banner).toHaveTextContent(/practice integration coach/i);
    expect(
      screen.getByRole("link", { name: /open chat/i }),
    ).toHaveAttribute("href", "/chat?system=practice");
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

// ─── Hydration (issue #312) ──────────────────────────────────────────

describe("PracticePage hydration", () => {
  it("reads the day's log for the user's local day", async () => {
    render(<PracticePage />);

    await waitFor(() => expect(mockListPracticeLog).toHaveBeenCalled());
    expect(mockListPracticeLog).toHaveBeenCalledWith(
      expect.objectContaining({
        from: "2026-08-14",
        to: "2026-08-14",
        perPage: 100,
      }),
    );
  });

  it("shows the cards in the state the log left them", async () => {
    mockListPracticeLog.mockResolvedValue(logPage([logEntry()]));

    render(<PracticePage />);

    const morning = await screen.findByRole("region", { name: /morning/i });
    expect(
      within(within(morning).getAllByRole("article")[0]).getByText(
        "Done today.",
      ),
    ).toBeInTheDocument();
    // The row named its slot, so it marks that card and no other.
    expect(screen.getAllByText("Done today.")).toHaveLength(1);
  });

  it("holds the cards back until the log has landed", async () => {
    let release: (value: PracticeLogListResponse) => void = () => {};
    mockListPracticeLog.mockReturnValue(
      new Promise<PracticeLogListResponse>((resolve) => {
        release = resolve;
      }),
    );

    render(<PracticePage />);

    await waitFor(() => expect(mockGetToday).toHaveBeenCalled());
    expect(
      screen.queryByRole("button", { name: /^done$/i }),
    ).not.toBeInTheDocument();

    await act(async () => {
      release(logPage([logEntry()]));
    });

    // Drawn settled the first time rather than flipped a moment later,
    // which would move focus onto a completion nobody just made.
    expect(await screen.findByText("Done today.")).toBeInTheDocument();
  });

  it("draws the cards anyway when the log cannot be read, and says so", async () => {
    mockListPracticeLog.mockRejectedValue(new Error("HTTP 500"));

    render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    expect(
      screen.getAllByRole("button", { name: /^done$/i }).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/may look untouched/i)).toBeInTheDocument();
  });

  it("reads the log again when the notice's retry is used", async () => {
    mockListPracticeLog.mockRejectedValueOnce(new Error("HTTP 500"));
    mockListPracticeLog.mockResolvedValue(logPage([logEntry()]));

    render(<PracticePage />);

    const notice = await screen.findByText(/may look untouched/i);
    fireEvent.click(
      within(notice.parentElement as HTMLElement).getByRole("button", {
        name: /try again/i,
      }),
    );

    expect(await screen.findByText("Done today.")).toBeInTheDocument();
    expect(screen.queryByText(/may look untouched/i)).not.toBeInTheDocument();
  });

  it("keeps what the user has done when the log is read again", async () => {
    // Retrying the log used to take the protocol back to its spinner,
    // which unmounts DailyProtocol and throws away every card: an
    // optimistic completion still in flight, and anything typed into a
    // prompt underneath it.
    mockListPracticeLog.mockRejectedValueOnce(new Error("HTTP 500"));
    mockListPracticeLog.mockResolvedValue(logPage([]));
    // The write stays in flight across the retry, which is the state
    // there is no recovering from once the card is gone.
    mockLogPractice.mockReturnValue(new Promise(() => {}));

    render(<PracticePage />);

    await screen.findByText(/may look untouched/i);
    const card = within(
      screen.getByRole("region", { name: /morning/i }),
    ).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /^done$/i }));
    expect(within(card).getByText("Done today.")).toBeInTheDocument();

    fireEvent.change(
      within(card).getByLabelText(/anything else worth writing down/i),
      { target: { value: "Half a thought." } },
    );

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    await waitFor(() =>
      expect(screen.queryByText(/may look untouched/i)).not.toBeInTheDocument(),
    );
    // Same card, not a replacement: the protocol never went back to a
    // spinner, so nothing on it was rebuilt.
    expect(card).toBeInTheDocument();
    expect(within(card).getByText("Done today.")).toBeInTheDocument();
    expect(
      within(card).getByLabelText(/anything else worth writing down/i),
    ).toHaveValue("Half a thought.");
    expect(
      screen.queryByText(/putting today's practice together/i),
    ).not.toBeInTheDocument();
  });

  it("merges a re-read log into the cards in place", async () => {
    mockListPracticeLog.mockRejectedValueOnce(new Error("HTTP 500"));
    mockListPracticeLog.mockResolvedValue(
      logPage([logEntry({ id: "log-evening", protocol_slot: "evening" })]),
    );
    mockLogPractice.mockResolvedValue(logEntry({ id: "log-morning" }));

    render(<PracticePage />);

    await screen.findByText(/may look untouched/i);
    const card = within(
      screen.getByRole("region", { name: /morning/i }),
    ).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /^done$/i }));
    await waitFor(() => expect(mockLogPractice).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /try again/i }));

    // The evening row arrives and lands on its own card; the morning one
    // the user tapped is left exactly as it was.
    await waitFor(() =>
      expect(
        within(
          within(screen.getByRole("region", { name: /evening/i })).getAllByRole(
            "article",
          )[0],
        ).getByText("Done today."),
      ).toBeInTheDocument(),
    );
    expect(within(card).getByText("Done today.")).toBeInTheDocument();
    expect(screen.getAllByText("Done today.")).toHaveLength(2);
  });

  it("does not fill the cards from part of a day", async () => {
    // More rows match than came back, so this page is a fragment of the
    // day and cards drawn from it would be guesswork.
    mockListPracticeLog.mockResolvedValue(logPage([logEntry()], { total: 150 }));

    render(<PracticePage />);

    await screen.findAllByText("Find the Floor");
    expect(screen.queryByText("Done today.")).not.toBeInTheDocument();
  });
});
