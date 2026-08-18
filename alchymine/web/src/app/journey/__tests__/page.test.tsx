import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import JourneyPage from "../page";
import {
  getJourneyTimeseries,
  type JourneyTimeseriesResponse,
} from "@/lib/api";
import { LOSS_AVERSION_BANNED } from "@/components/practice/PracticeRhythm";

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
    user: { id: "user-1", email: "test@example.com" },
    isLoading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    getJourneyTimeseries: jest.fn(),
  };
});

const mockGet = getJourneyTimeseries as jest.Mock;

function day(
  dayKey: string,
  overrides: Partial<JourneyTimeseriesResponse["days"][number]> = {},
) {
  return {
    day_key: dayKey,
    completed: 0,
    purposes: [] as string[],
    loops: 0,
    average_shift: null as number | null,
    ...overrides,
  };
}

/** Seven consecutive days ending 2026-08-18, the shape the API returns. */
const WEEK = [
  "2026-08-12",
  "2026-08-13",
  "2026-08-14",
  "2026-08-15",
  "2026-08-16",
  "2026-08-17",
  "2026-08-18",
];

function response(
  overrides: Partial<JourneyTimeseriesResponse> = {},
): JourneyTimeseriesResponse {
  return {
    day_key: "2026-08-18",
    start_day: "2026-08-12",
    window_days: 7,
    days: WEEK.map((key) => day(key)),
    by_purpose: {
      "self-knowledge": 0,
      steadiness: 0,
      stewardship: 0,
      expression: 0,
      reframing: 0,
    },
    totals: {
      days_practiced: 0,
      completed: 0,
      loops_closed: 0,
      first_practice_day: null,
      first_loop_day: null,
    },
    ...overrides,
  };
}

/** A user with real history: two practices, one closed loop. */
function withHistory(): JourneyTimeseriesResponse {
  return response({
    days: [
      day("2026-08-12"),
      day("2026-08-13"),
      day("2026-08-14"),
      day("2026-08-15", {
        completed: 2,
        purposes: ["steadiness", "expression"],
        loops: 1,
        average_shift: 1.5,
      }),
      day("2026-08-16"),
      day("2026-08-17"),
      day("2026-08-18", { completed: 1, purposes: ["reframing"] }),
    ],
    by_purpose: {
      "self-knowledge": 0,
      steadiness: 1,
      stewardship: 0,
      expression: 1,
      reframing: 1,
    },
    totals: {
      days_practiced: 2,
      completed: 3,
      loops_closed: 1,
      first_practice_day: "2026-03-04",
      first_loop_day: "2026-03-09",
    },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGet.mockResolvedValue(response());
});

describe("JourneyPage shell", () => {
  it("renders the page heading", async () => {
    render(<JourneyPage />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
        /Your journey/i,
      );
    });
  });

  it("has a back link to the dashboard", async () => {
    render(<JourneyPage />);
    const link = await screen.findByRole("link", {
      name: /back to dashboard/i,
    });
    expect(link).toHaveAttribute("href", "/dashboard");
  });

  it("asks the API for the caller's local day and the default window", async () => {
    render(<JourneyPage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    const [today, days] = mockGet.mock.calls[0];
    expect(today).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(days).toBe(30);
  });
});

describe("JourneyPage async states", () => {
  it("shows a loading state before the series arrives", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<JourneyPage />);

    expect(screen.getByRole("status")).toHaveTextContent(
      /loading your journey/i,
    );
  });

  it("shows a recoverable error state rather than a blank page", async () => {
    mockGet.mockRejectedValue(new Error("Request timed out."));
    render(<JourneyPage />);

    expect(await screen.findByText(/could not load data/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("retries the request when the error state is dismissed", async () => {
    mockGet.mockRejectedValueOnce(new Error("nope"));
    mockGet.mockResolvedValue(withHistory());
    render(<JourneyPage />);

    fireEvent.click(await screen.findByRole("button", { name: /try again/i }));

    expect(
      await screen.findByRole("heading", { name: /practice and integration/i }),
    ).toBeInTheDocument();
  });

  it("shows no raw error object when the message is not a plain string", async () => {
    mockGet.mockRejectedValue(new Error("[object Object]"));
    render(<JourneyPage />);

    await screen.findByText(/could not load data/i);
    expect(screen.queryByText(/traceback/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/File "/)).not.toBeInTheDocument();
  });
});

describe("JourneyPage empty state", () => {
  it("invites a first practice when nothing has ever been logged", async () => {
    render(<JourneyPage />);

    expect(
      await screen.findByRole("heading", {
        name: /your journey starts with one practice/i,
      }),
    ).toBeInTheDocument();
  });

  it("points at the practice page", async () => {
    render(<JourneyPage />);

    const link = await screen.findByRole("link", {
      name: /go to today's practice/i,
    });
    expect(link).toHaveAttribute("href", "/practice");
  });

  it("draws no chart, because there is nothing to draw", async () => {
    render(<JourneyPage />);
    await screen.findByRole("heading", { name: /starts with one practice/i });

    expect(
      screen.queryByRole("heading", { name: /practice and integration/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps a quiet window separate from never having started", async () => {
    // Zero in the window, but a log going back to March: a real reader
    // with a quiet month, not a new user.
    mockGet.mockResolvedValue(
      response({
        totals: {
          days_practiced: 0,
          completed: 0,
          loops_closed: 0,
          first_practice_day: "2026-03-04",
          first_loop_day: null,
        },
      }),
    );
    render(<JourneyPage />);

    expect(
      await screen.findByRole("heading", { name: /practice and integration/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /starts with one practice/i }),
    ).not.toBeInTheDocument();
  });
});

describe("JourneyPage series", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(withHistory());
  });

  it("renders the window totals", async () => {
    render(<JourneyPage />);
    const totals = await screen.findByRole("region", { name: /these 7 days/i });

    expect(within(totals).getByText("3")).toBeInTheDocument();
    expect(within(totals).getByText("Practices")).toBeInTheDocument();
    expect(within(totals).getByText("Loops closed")).toBeInTheDocument();
  });

  it("names the day the user started, which is older than the window", async () => {
    render(<JourneyPage />);
    const totals = await screen.findByRole("region", { name: /these 7 days/i });

    expect(totals).toHaveTextContent(/Practicing since 4 March 2026/i);
    expect(totals).toHaveTextContent(/First loop closed on 9 March 2026/i);
  });

  it("gives every column of the chart a text description", async () => {
    render(<JourneyPage />);
    await screen.findByRole("heading", { name: /practice and integration/i });

    expect(
      screen.getByText(
        /Saturday 15 August: 2 practices completed \(Steadiness, Expression\), 1 loop closed, recorded shift \+1\.5\./i,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Wednesday 12 August: nothing logged\./i),
    ).toBeInTheDocument();
  });

  it("renders all five capacities with their counts", async () => {
    render(<JourneyPage />);
    const balance = await screen.findByRole("region", {
      name: /where the practice went/i,
    });

    for (const label of [
      "Self-knowledge",
      "Steadiness",
      "Stewardship",
      "Expression",
      "Reframing",
    ]) {
      expect(within(balance).getByText(label)).toBeInTheDocument();
    }
  });
});

describe("JourneyPage window picker", () => {
  beforeEach(() => {
    mockGet.mockResolvedValue(withHistory());
  });

  it("offers the three windows the server accepts", async () => {
    render(<JourneyPage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    for (const label of [/7 days/, /30 days/, /90 days/]) {
      expect(screen.getByRole("radio", { name: label })).toBeInTheDocument();
    }
  });

  it("opens on thirty days", async () => {
    render(<JourneyPage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    expect(screen.getByRole("radio", { name: /30 days/ })).toBeChecked();
  });

  it("refetches with the chosen window", async () => {
    render(<JourneyPage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("radio", { name: /90 days/ }));

    await waitFor(() => {
      expect(mockGet).toHaveBeenLastCalledWith(
        expect.any(String),
        90,
        expect.anything(),
      );
    });
  });
});

describe("JourneyPage copy", () => {
  it.each([
    ["with history", withHistory],
    ["with nothing logged", response],
  ])("uses no loss-aversion language %s", async (_name, build) => {
    mockGet.mockResolvedValue(build());
    const { container } = render(<JourneyPage />);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    const text = (container.textContent ?? "").toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(text).not.toContain(banned);
    }
  });
});
