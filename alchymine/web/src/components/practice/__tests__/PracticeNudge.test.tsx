import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import PracticeNudge, {
  NUDGE_DISMISS_PREFIX,
  remainingPractices,
} from "../PracticeNudge";
import { LOSS_AVERSION_BANNED } from "../PracticeRhythm";
import { localDayKey } from "@/lib/localDay";
import type {
  PracticeLogEntry,
  PracticeLogListResponse,
  ProtocolItem,
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

const mockGetToday = jest.fn();
const mockListLog = jest.fn();

jest.mock("@/lib/api", () => ({
  getPracticeToday: (...args: unknown[]) => mockGetToday(...args),
  listPracticeLog: (...args: unknown[]) => mockListLog(...args),
}));

// ─── Fixtures ────────────────────────────────────────────────────────

function item(slug: string): ProtocolItem {
  return {
    pack_id: "alchymine-foundations",
    slug,
    title: `Practice ${slug}`,
    summary: "One line about the practice.",
    purpose: "steadiness",
    purposes: ["steadiness"],
    category: "somatic",
    duration_minutes: 5,
    reason: "Balancing your week.",
    reason_template: "balance",
  };
}

function today(slugs: string[]): TodayResponse {
  return {
    day_key: localDayKey(),
    generated_at: "2026-08-18T08:00:00+00:00",
    protocol_size: slugs.length,
    items: slugs.map(item),
    slots: {},
  };
}

function logEntry(slug: string): PracticeLogEntry {
  return {
    id: `log-${slug}`,
    user_id: "test-user",
    pack_id: "alchymine-foundations",
    practice_slug: slug,
    primary_purpose: "steadiness",
    purposes: ["steadiness"],
    category: "somatic",
    status: "completed",
    protocol_slot: "morning",
    duration_minutes: 5,
    occurred_at: "2026-08-18T09:00:00+00:00",
    day_key: localDayKey(),
    created_at: "2026-08-18T09:00:00+00:00",
    reflection: null,
    self_check_response: null,
  };
}

function logList(slugs: string[]): PracticeLogListResponse {
  const entries = slugs.map(logEntry);
  return { entries, total: entries.length, page: 1, per_page: 100 };
}

/** Let every settled promise in the component's chain land. */
async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

const NUDGE = "practice-nudge";

beforeEach(() => {
  localStorage.clear();
  mockGetToday.mockReset();
  mockListLog.mockReset();
  mockGetToday.mockResolvedValue(today(["find-the-floor", "name-the-weather"]));
  mockListLog.mockResolvedValue(logList([]));
});

// ─── Trigger ─────────────────────────────────────────────────────────

describe("PracticeNudge trigger", () => {
  it("invites the user back when today's protocol has practices left", async () => {
    render(<PracticeNudge />);

    expect(await screen.findByTestId(NUDGE)).toBeInTheDocument();
  });

  it("still shows when only some of today's protocol is done", async () => {
    mockListLog.mockResolvedValue(logList(["find-the-floor"]));
    render(<PracticeNudge />);

    expect(await screen.findByTestId(NUDGE)).toBeInTheDocument();
  });

  it("renders nothing when every practice in the protocol is done today", async () => {
    mockListLog.mockResolvedValue(
      logList(["find-the-floor", "name-the-weather"]),
    );
    render(<PracticeNudge />);

    await waitFor(() => expect(mockListLog).toHaveBeenCalled());
    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
  });

  it("renders nothing when there is no protocol today", async () => {
    mockGetToday.mockResolvedValue(today([]));
    render(<PracticeNudge />);

    await waitFor(() => expect(mockGetToday).toHaveBeenCalled());
    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
  });

  it("renders nothing while its data is still loading", async () => {
    mockGetToday.mockReturnValue(new Promise(() => {}));
    mockListLog.mockReturnValue(new Promise(() => {}));
    render(<PracticeNudge />);

    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
    // A nudge that is still thinking says nothing at all: no spinner,
    // no skeleton, no reserved space.
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("renders nothing when the protocol read fails", async () => {
    mockGetToday.mockRejectedValue(new Error("network"));
    render(<PracticeNudge />);

    await waitFor(() => expect(mockGetToday).toHaveBeenCalled());
    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders nothing when the practice log read fails", async () => {
    mockListLog.mockRejectedValue(new Error("network"));
    render(<PracticeNudge />);

    await waitFor(() => expect(mockListLog).toHaveBeenCalled());
    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("reads only today, and only completions", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const dayKey = localDayKey();
    expect(mockGetToday).toHaveBeenCalledWith(
      dayKey,
      expect.objectContaining({ signal: expect.anything() }),
    );
    expect(mockListLog).toHaveBeenCalledWith(
      expect.objectContaining({
        from: dayKey,
        to: dayKey,
        status: "completed",
      }),
    );
  });

  it("stays quiet when more was logged than one page can show", async () => {
    // The page cap is a display bound, not a fact about the user. If the
    // day holds more completions than came back, the honest read is that
    // plenty happened, so the nudge steps aside rather than guessing.
    mockListLog.mockResolvedValue({
      ...logList(["find-the-floor"]),
      total: 250,
    });
    render(<PracticeNudge />);

    await waitFor(() => expect(mockListLog).toHaveBeenCalled());
    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
  });
});

// ─── Dismissal ───────────────────────────────────────────────────────

describe("PracticeNudge dismissal", () => {
  it("hides once dismissed and records the day", async () => {
    render(<PracticeNudge />);
    const nudge = await screen.findByTestId(NUDGE);
    expect(nudge).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

    await waitFor(() =>
      expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument(),
    );
    expect(
      localStorage.getItem(`${NUDGE_DISMISS_PREFIX}${localDayKey()}`),
    ).not.toBeNull();
  });

  it("stays hidden on a later visit the same day", async () => {
    localStorage.setItem(`${NUDGE_DISMISS_PREFIX}${localDayKey()}`, "1");
    render(<PracticeNudge />);

    await flush();
    expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument();
  });

  it("asks for nothing once the day has been dismissed", async () => {
    // A dismissed nudge is not a cheaper nudge, it is no nudge: it must
    // not spend two requests on the dashboard to decide to say nothing.
    localStorage.setItem(`${NUDGE_DISMISS_PREFIX}${localDayKey()}`, "1");
    render(<PracticeNudge />);

    await flush();
    expect(mockGetToday).not.toHaveBeenCalled();
    expect(mockListLog).not.toHaveBeenCalled();
  });

  it("comes back on a new day", async () => {
    // Yesterday's dismissal is keyed to yesterday, so it says nothing
    // about today.
    localStorage.setItem(`${NUDGE_DISMISS_PREFIX}2020-01-01`, "1");
    render(<PracticeNudge />);

    expect(await screen.findByTestId(NUDGE)).toBeInTheDocument();
  });

  it("still shows when localStorage cannot be read", async () => {
    const getItem = jest
      .spyOn(Storage.prototype, "getItem")
      .mockImplementation(() => {
        throw new Error("private mode");
      });
    try {
      render(<PracticeNudge />);
      expect(await screen.findByTestId(NUDGE)).toBeInTheDocument();
    } finally {
      getItem.mockRestore();
    }
  });

  it("still hides when the dismissal cannot be written", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const setItem = jest
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("quota");
      });
    try {
      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
      await waitFor(() =>
        expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument(),
      );
    } finally {
      setItem.mockRestore();
    }
  });
});

// ─── Accessibility ───────────────────────────────────────────────────

describe("PracticeNudge accessibility", () => {
  it("is a complementary landmark with an accessible name", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const landmark = screen.getByRole("complementary");
    expect(landmark).toHaveAccessibleName();
  });

  it("carries a heading rather than an orphaned block of text", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    // h2: the dashboard owns the h1 and its cards are h2, so the nudge
    // sits at the same level rather than skipping one.
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });

  it("gives the dismiss control a real button and an aria-label", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const dismiss = screen.getByRole("button", { name: /dismiss/i });
    expect(dismiss.tagName).toBe("BUTTON");
    expect(dismiss).toHaveAttribute("type", "button");
    expect(dismiss).toHaveAttribute("aria-label");
  });

  it("puts the dismiss control in the tab order with a visible focus ring", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const dismiss = screen.getByRole("button", { name: /dismiss/i });
    expect(dismiss).not.toHaveAttribute("tabindex", "-1");
    expect(dismiss.className).toContain("focus-visible:ring-2");

    dismiss.focus();
    expect(dismiss).toHaveFocus();
  });

  it("dismisses from the keyboard", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const dismiss = screen.getByRole("button", { name: /dismiss/i });
    dismiss.focus();
    expect(dismiss).toHaveFocus();

    // A focused native button activates on Enter and Space, which the
    // browser delivers as a click. jsdom does not synthesize that, so
    // the keydown and the resulting click are both sent here.
    fireEvent.keyDown(dismiss, { key: "Enter", code: "Enter" });
    fireEvent.click(dismiss);

    await waitFor(() =>
      expect(screen.queryByTestId(NUDGE)).not.toBeInTheDocument(),
    );
  });

  it("links to the practice page without opening a new context", async () => {
    render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/practice");
    expect(link).not.toHaveAttribute("target");
  });

  it("animates nothing", async () => {
    const { container } = render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    expect(container.innerHTML).not.toContain("animate-");
    expect(container.innerHTML).not.toContain("transition-transform");
  });
});

// ─── Copy ────────────────────────────────────────────────────────────

describe("PracticeNudge copy", () => {
  it("renders no loss-aversion language", async () => {
    const { container } = render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const rendered = container.innerHTML.toLowerCase();
    for (const banned of LOSS_AVERSION_BANNED) {
      expect(rendered).not.toContain(banned);
    }
  });

  it("counts nothing at the user", async () => {
    // "2 of 5 left" turns an invitation into a progress bar with a
    // shortfall in it. The nudge names no numbers.
    mockListLog.mockResolvedValue(logList(["find-the-floor"]));
    const { container } = render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    expect(container.textContent).not.toMatch(/\d/);
  });

  it("uses no urgency or obligation language", async () => {
    const { container } = render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    const text = (container.textContent ?? "").toLowerCase();
    for (const banned of [
      "hurry",
      "last chance",
      "expires",
      "only today",
      "you should",
      "you must",
      "don't forget",
      "dont forget",
      "falling behind",
      "catch up",
    ]) {
      expect(text).not.toContain(banned);
    }
  });

  it("uses no em-dashes", async () => {
    const { container } = render(<PracticeNudge />);
    await screen.findByTestId(NUDGE);

    expect(container.textContent).not.toContain("—");
  });
});

// ─── The pure trigger helper ─────────────────────────────────────────

describe("remainingPractices", () => {
  const protocol = [item("a"), item("b")];

  it("returns everything when nothing has been completed", () => {
    expect(remainingPractices(protocol, [])).toHaveLength(2);
  });

  it("drops a practice once it has a completed row", () => {
    const remaining = remainingPractices(protocol, [logEntry("a")]);
    expect(remaining.map((entry) => entry.slug)).toEqual(["b"]);
  });

  it("returns nothing when the whole protocol is done", () => {
    expect(
      remainingPractices(protocol, [logEntry("a"), logEntry("b")]),
    ).toHaveLength(0);
  });

  it("counts a completion only within its own pack", () => {
    // Two packs can carry the same slug. Matching on the slug alone
    // would let one pack's practice tick off another's.
    const foreign = { ...logEntry("a"), pack_id: "somebody-elses-pack" };
    expect(remainingPractices(protocol, [foreign])).toHaveLength(2);
  });

  it("ignores rows that are not completions", () => {
    // A skip is an honest answer, not a completion. The user said no to
    // this one today, so it does not count as done.
    const skipped = { ...logEntry("a"), status: "skipped" };
    expect(remainingPractices(protocol, [skipped])).toHaveLength(2);
  });
});
