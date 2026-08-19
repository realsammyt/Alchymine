import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import DailyProtocol from "../DailyProtocol";
import { remainingPractices } from "../PracticeNudge";
import { ApiError } from "@/lib/api";
import type {
  PracticeDefinition,
  PracticeLogEntry,
  ProtocolItem,
  TodayResponse,
} from "@/lib/api";

const FLOOR: ProtocolItem = {
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
};

const PATTERN: ProtocolItem = {
  pack_id: "alchymine-foundations",
  slug: "name-the-pattern",
  title: "Name the Pattern",
  summary: "Catch the shape of a loop while it is still running.",
  purpose: "self-knowledge",
  purposes: ["self-knowledge"],
  category: "reflection",
  duration_minutes: 10,
  reason: "It has been 16 days.",
  reason_template: "staleness",
};

const TODAY: TodayResponse = {
  day_key: "2026-08-14",
  generated_at: "2026-08-14T08:00:00+00:00",
  protocol_size: 2,
  items: [FLOOR, PATTERN],
  slots: {
    morning: [
      { pack_id: FLOOR.pack_id, slug: FLOOR.slug, prompt: "Morning floor prompt" },
      {
        pack_id: PATTERN.pack_id,
        slug: PATTERN.slug,
        prompt: "Morning pattern prompt",
      },
    ],
    day: [
      { pack_id: FLOOR.pack_id, slug: FLOOR.slug, prompt: "Midday floor prompt" },
      {
        pack_id: PATTERN.pack_id,
        slug: PATTERN.slug,
        prompt: "Midday pattern prompt",
      },
    ],
    evening: [
      { pack_id: FLOOR.pack_id, slug: FLOOR.slug, prompt: "Evening floor prompt" },
      {
        pack_id: PATTERN.pack_id,
        slug: PATTERN.slug,
        prompt: "Evening pattern prompt",
      },
    ],
  },
};

const FLOOR_DEFINITION = {
  slug: "find-the-floor",
  title: "Find the Floor",
  self_check: {
    failure_mode: "It turns into a way to get rid of a feeling.",
    question: "Were you settling, or were you trying to make something go away?",
  },
} as unknown as PracticeDefinition;

function logEntry(overrides: Partial<PracticeLogEntry> = {}): PracticeLogEntry {
  return {
    id: "log-1",
    user_id: "user-1",
    pack_id: FLOOR.pack_id,
    practice_slug: FLOOR.slug,
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

function renderProtocol(
  overrides: Partial<React.ComponentProps<typeof DailyProtocol>> = {},
) {
  const props = {
    today: TODAY,
    lookup: (_packId: string, slug: string) =>
      slug === "find-the-floor" ? FLOOR_DEFINITION : undefined,
    onLog: jest.fn().mockResolvedValue(logEntry()),
    onIntegrate: jest.fn().mockResolvedValue(undefined),
    onLogged: jest.fn(),
    ...overrides,
  };
  return { ...render(<DailyProtocol {...props} />), props };
}

function morningSection() {
  return screen.getByRole("region", { name: /morning/i });
}

describe("DailyProtocol slots", () => {
  it("renders one section per slot", () => {
    renderProtocol();

    expect(screen.getByRole("region", { name: /morning/i })).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /during the day/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /evening/i })).toBeInTheDocument();
  });

  it("renders every practice in every slot", () => {
    renderProtocol();
    expect(screen.getAllByText("Find the Floor")).toHaveLength(3);
    expect(screen.getAllByText("Name the Pattern")).toHaveLength(3);
  });

  it("gives each slot its own positional prompt", () => {
    renderProtocol();

    expect(
      within(morningSection()).getByText("Morning floor prompt"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: /evening/i })).getByText(
        "Evening floor prompt",
      ),
    ).toBeInTheDocument();
  });

  it("shows an empty state when the protocol has no practices", () => {
    renderProtocol({
      today: { ...TODAY, items: [], slots: { morning: [], day: [], evening: [] } },
    });

    expect(
      screen.getByText(/nothing scheduled|no practices/i),
    ).toBeInTheDocument();
  });
});

describe("DailyProtocol completion", () => {
  it("marks the card done before the write resolves", async () => {
    let release: (value: PracticeLogEntry) => void = () => {};
    const onLog = jest.fn(
      () =>
        new Promise<PracticeLogEntry>((resolve) => {
          release = resolve;
        }),
    );
    renderProtocol({ onLog });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    expect(within(card).getByText("Done today.")).toBeInTheDocument();

    release(logEntry());
    await waitFor(() => expect(onLog).toHaveBeenCalled());
  });

  it("posts the slot and the local day with the completion", async () => {
    const { props } = renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() => expect(props.onLog).toHaveBeenCalled());
    expect(props.onLog).toHaveBeenCalledWith(
      expect.objectContaining({
        pack_id: FLOOR.pack_id,
        practice_slug: FLOOR.slug,
        day_key: "2026-08-14",
        status: "completed",
        protocol_slot: "morning",
      }),
    );
  });

  it("rolls the card back and explains when the write fails", async () => {
    const onLog = jest.fn().mockRejectedValue(new Error("HTTP 500"));
    renderProtocol({ onLog });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(within(card).queryByText("Done today.")).not.toBeInTheDocument(),
    );
    expect(
      within(card).getByText(/didn't save/i),
    ).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: /done/i })).toBeEnabled();
  });

  it("tells the page a write landed so the rhythm can refresh", async () => {
    const { props } = renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() => expect(props.onLogged).toHaveBeenCalled());
  });

  it("does not fire onLogged when the write failed", async () => {
    const onLog = jest.fn().mockRejectedValue(new Error("HTTP 500"));
    const { props } = renderProtocol({ onLog });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() => expect(onLog).toHaveBeenCalled());
    expect(props.onLogged).not.toHaveBeenCalled();
  });

  it("completes one slot without touching the same practice elsewhere", async () => {
    renderProtocol();

    const morningCard = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(
      within(morningCard).getByRole("button", { name: /done/i }),
    );

    const eveningCard = within(
      screen.getByRole("region", { name: /evening/i }),
    ).getAllByRole("article")[0];
    expect(
      within(eveningCard).queryByText("Done today."),
    ).not.toBeInTheDocument();
  });
});

describe("DailyProtocol skipping", () => {
  it("writes a skipped row with no penalty copy", async () => {
    const { props, container } = renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /not today/i }));

    await waitFor(() =>
      expect(props.onLog).toHaveBeenCalledWith(
        expect.objectContaining({ status: "skipped" }),
      ),
    );
    expect(container.innerHTML.toLowerCase()).not.toContain("streak");
  });
});

describe("DailyProtocol follow-ups", () => {
  it("offers the self-check only after a completion", async () => {
    renderProtocol();

    expect(
      screen.queryByText(FLOOR_DEFINITION.self_check.question),
    ).not.toBeInTheDocument();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(
        within(card).getByText(FLOOR_DEFINITION.self_check.question),
      ).toBeInTheDocument(),
    );
  });

  it("offers the integration prompt after a completion", async () => {
    renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(
        within(card).getByRole("link", { name: /journal/i }),
      ).toBeInTheDocument(),
    );
  });

  it("keeps focus inside the card when a practice is completed", async () => {
    renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    const done = within(card).getByRole("button", { name: /done/i });
    done.focus();
    fireEvent.click(done);

    // The card's own status region is first in document order; the
    // follow-up prompts each add their own further down.
    await waitFor(() =>
      expect(within(card).getAllByRole("status")[0]).toHaveFocus(),
    );
    expect(within(card).getAllByRole("status")[0]).toHaveTextContent(
      "Done today.",
    );
  });

  it("confirms the self-check instead of unmounting it", async () => {
    renderProtocol();

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    await waitFor(() =>
      expect(
        within(card).getByRole("button", { name: "Save this" }),
      ).toBeInTheDocument(),
    );

    fireEvent.change(within(card).getByLabelText(FLOOR_DEFINITION.self_check.question), {
      target: { value: "Settling, mostly." },
    });
    fireEvent.click(within(card).getByRole("button", { name: "Save this" }));

    await waitFor(() =>
      expect(
        within(card).getByText("Saved. Only you see this."),
      ).toBeInTheDocument(),
    );
  });

  it("posts the integration against the practice log row that was created", async () => {
    const { props } = renderProtocol({
      onLog: jest.fn().mockResolvedValue(logEntry({ id: "log-99" })),
    });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    // "Save" exactly: the self-check's control is "Save this", and this
    // assertion is about the integration write, not that one.
    await waitFor(() =>
      expect(within(card).getByRole("button", { name: "Save" })).toBeInTheDocument(),
    );
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(props.onIntegrate).toHaveBeenCalledWith(
        expect.objectContaining({ practice_log_id: "log-99" }),
      ),
    );
  });

  it("saves both prompts against the one completion", async () => {
    const { props } = renderProtocol({
      onLog: jest.fn().mockResolvedValue(logEntry({ id: "log-99" })),
    });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    await waitFor(() =>
      expect(
        within(card).getByRole("button", { name: "Save this" }),
      ).toBeInTheDocument(),
    );

    fireEvent.change(
      within(card).getByLabelText(FLOOR_DEFINITION.self_check.question),
      { target: { value: "Settling, mostly." } },
    );
    fireEvent.click(within(card).getByRole("button", { name: "Save this" }));
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    // Two writes, one completion. The server keys the record on the
    // practice log row, so both land on the same one.
    await waitFor(() => expect(props.onIntegrate).toHaveBeenCalledTimes(2));
    expect(props.onIntegrate).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ practice_log_id: "log-99" }),
    );
    expect(props.onIntegrate).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ practice_log_id: "log-99" }),
    );

    expect(
      within(card).getByText("Saved. Only you see this."),
    ).toBeInTheDocument();
    expect(
      within(card).getByText("Logged. It'll show up on your dashboard."),
    ).toBeInTheDocument();
  });

  it("does not let the two saves for one card overlap", async () => {
    // Both prompts write to the same record, and the note on it is the
    // merge of what each one sent. Overlapping writes would have the
    // second read the record before the first had written to it, and
    // one of the two notes would be lost.
    let releaseFirst: (() => void) | undefined;
    const onIntegrate = jest.fn().mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          if (!releaseFirst) releaseFirst = () => resolve();
          else resolve();
        }),
    );
    renderProtocol({
      onLog: jest.fn().mockResolvedValue(logEntry({ id: "log-99" })),
      onIntegrate,
    });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    await waitFor(() =>
      expect(
        within(card).getByRole("button", { name: "Save this" }),
      ).toBeInTheDocument(),
    );

    fireEvent.change(
      within(card).getByLabelText(FLOOR_DEFINITION.self_check.question),
      { target: { value: "Settling, mostly." } },
    );
    fireEvent.click(within(card).getByRole("button", { name: "Save this" }));
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onIntegrate).toHaveBeenCalledTimes(1));
    expect(onIntegrate).toHaveBeenCalledTimes(1);

    releaseFirst?.();
    await waitFor(() => expect(onIntegrate).toHaveBeenCalledTimes(2));
  });

  it("keeps the integration prompt usable after the self-check is saved", async () => {
    const { props } = renderProtocol({
      onLog: jest.fn().mockResolvedValue(logEntry({ id: "log-99" })),
    });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    await waitFor(() =>
      expect(
        within(card).getByRole("button", { name: "Save this" }),
      ).toBeInTheDocument(),
    );

    fireEvent.change(
      within(card).getByLabelText(FLOOR_DEFINITION.self_check.question),
      { target: { value: "Settling, mostly." } },
    );
    fireEvent.click(within(card).getByRole("button", { name: "Save this" }));
    await waitFor(() =>
      expect(
        within(card).getByText("Saved. Only you see this."),
      ).toBeInTheDocument(),
    );

    fireEvent.click(within(card).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(props.onIntegrate).toHaveBeenCalledTimes(2));
    expect(props.onIntegrate).toHaveBeenLastCalledWith(
      expect.objectContaining({ practice_log_id: "log-99" }),
    );
  });

  it("shows no self-check when the definition is not loaded", async () => {
    renderProtocol({ lookup: () => undefined });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(within(card).getByText("Done today.")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(FLOOR_DEFINITION.self_check.question),
    ).not.toBeInTheDocument();
  });
});

// ─── Hydration (issue #312) ──────────────────────────────────────────
//
// Completions used to live only in component state, so a reload handed
// back a day of untouched cards while the rows sat in the log and the
// nudge on the home page correctly stepped aside. The cards now start
// in the state the day's log says they are in.

function eveningSection() {
  return screen.getByRole("region", { name: /evening/i });
}

describe("DailyProtocol hydration", () => {
  it("mounts a card done when the day's log has a completion for it", () => {
    renderProtocol({ loggedToday: [logEntry()] });

    expect(
      within(within(morningSection()).getAllByRole("article")[0]).getByText(
        "Done today.",
      ),
    ).toBeInTheDocument();
  });

  it("mounts a card as a skip when that is what the row says", () => {
    renderProtocol({ loggedToday: [logEntry({ status: "skipped" })] });

    expect(
      within(within(morningSection()).getAllByRole("article")[0]).getByText(
        "Not today. That's fine.",
      ),
    ).toBeInTheDocument();
  });

  it("marks only the slot the row was logged from", () => {
    renderProtocol({ loggedToday: [logEntry()] });

    expect(
      within(within(eveningSection()).getAllByRole("article")[0]).queryByText(
        "Done today.",
      ),
    ).not.toBeInTheDocument();
    expect(screen.getAllByText("Done today.")).toHaveLength(1);
  });

  it("offers the follow-ups against the row the log came back with", async () => {
    const { props } = renderProtocol({
      loggedToday: [logEntry({ id: "log-77" })],
    });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(props.onIntegrate).toHaveBeenCalledWith(
        expect.objectContaining({ practice_log_id: "log-77" }),
      ),
    );
  });

  it("fills the earliest free slot for a row that names none", () => {
    renderProtocol({ loggedToday: [logEntry({ protocol_slot: null })] });

    expect(
      within(within(morningSection()).getAllByRole("article")[0]).getByText(
        "Done today.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Done today.")).toHaveLength(1);
  });

  it("gives two unscheduled rows for one practice two different slots", () => {
    renderProtocol({
      loggedToday: [
        logEntry({ id: "log-2", protocol_slot: "unscheduled" }),
        logEntry({ id: "log-1", protocol_slot: null }),
      ],
    });

    expect(screen.getAllByText("Done today.")).toHaveLength(2);
  });

  it("keeps a slotted row on its own card and puts an unslotted one elsewhere", () => {
    renderProtocol({
      loggedToday: [
        logEntry({ id: "log-evening", protocol_slot: "evening" }),
        logEntry({ id: "log-loose", protocol_slot: null }),
      ],
    });

    expect(
      within(within(eveningSection()).getAllByRole("article")[0]).getByText(
        "Done today.",
      ),
    ).toBeInTheDocument();
    // The unslotted row took the earliest free slot rather than shoving
    // the slotted one off the card it names.
    expect(
      within(within(morningSection()).getAllByRole("article")[0]).getByText(
        "Done today.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Done today.")).toHaveLength(2);
  });

  it("ignores a row for a practice today's protocol does not carry", () => {
    renderProtocol({
      loggedToday: [logEntry({ practice_slug: "rotated-out-of-today" })],
    });

    expect(screen.queryByText("Done today.")).not.toBeInTheDocument();
  });

  it("keeps the newest row for a card and leaves the older one alone", () => {
    // Newest first, which is the order the route returns.
    renderProtocol({
      loggedToday: [
        logEntry({ id: "log-new", status: "skipped" }),
        logEntry({ id: "log-old", status: "completed" }),
      ],
    });

    expect(
      within(within(morningSection()).getAllByRole("article")[0]).getByText(
        "Not today. That's fine.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Done today.")).not.toBeInTheDocument();
  });

  it("leaves every card alone when the log could not be read", () => {
    renderProtocol({ loggedToday: null });

    expect(screen.queryByText("Done today.")).not.toBeInTheDocument();
    expect(
      within(morningSection()).getAllByRole("button", { name: /done/i }).length,
    ).toBeGreaterThan(0);
  });

  it("does not push back a card the user has already tapped", async () => {
    const onLog = jest.fn().mockResolvedValue(logEntry());
    const props = {
      today: TODAY,
      lookup: () => undefined,
      onLog,
      onIntegrate: jest.fn(),
      onLogged: jest.fn(),
    };
    const { rerender } = render(
      <DailyProtocol {...props} loggedToday={null} />,
    );

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));
    await waitFor(() => expect(onLog).toHaveBeenCalled());

    // A late read that has not caught up with what the user just did.
    rerender(
      <DailyProtocol
        {...props}
        loggedToday={[logEntry({ status: "skipped" })]}
      />,
    );

    expect(within(card).getByText("Done today.")).toBeInTheDocument();
  });

  it("hydrates cards from the same log that empties the nudge", () => {
    // The heart of #312: one log, two surfaces, one story. The nudge
    // reads the practices off the log and steps aside; the cards have to
    // show the same completions rather than a clean slate.
    const log = [
      logEntry({ id: "log-floor" }),
      logEntry({ id: "log-pattern", practice_slug: PATTERN.slug }),
    ];

    expect(remainingPractices(TODAY.items, log)).toHaveLength(0);

    renderProtocol({ loggedToday: log });
    expect(screen.getAllByText("Done today.")).toHaveLength(2);
  });
});

// ─── Refused saves ───────────────────────────────────────────────────

/** The server's own wording when an entry's note has no room left. */
const NOTE_FULL =
  "This entry's note is full. Your earlier notes are saved. This new text was not " +
  "added, so copy it somewhere safe if you want to keep it.";

describe("DailyProtocol refused saves", () => {
  it("passes on the server's reason when the note is full", async () => {
    const onIntegrate = jest.fn().mockRejectedValue(new ApiError(422, NOTE_FULL));
    renderProtocol({ onIntegrate, loggedToday: [logEntry({ id: "log-77" })] });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(within(card).getByText(NOTE_FULL)).toBeInTheDocument(),
    );
    // "Have another go" would be a lie: the note is full and the next
    // attempt is refused the same way.
    expect(within(card).queryByText(/another go/i)).not.toBeInTheDocument();
  });

  it("passes on the server's reason when the self-check is refused", async () => {
    const onIntegrate = jest.fn().mockRejectedValue(new ApiError(422, NOTE_FULL));
    renderProtocol({ onIntegrate, loggedToday: [logEntry({ id: "log-77" })] });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.change(
      within(card).getByLabelText(FLOOR_DEFINITION.self_check.question),
      { target: { value: "Settling, mostly." } },
    );
    fireEvent.click(within(card).getByRole("button", { name: "Save this" }));

    await waitFor(() =>
      expect(within(card).getByText(NOTE_FULL)).toBeInTheDocument(),
    );
  });

  it("keeps the retry line for a failure worth retrying", async () => {
    const onIntegrate = jest.fn().mockRejectedValue(new Error("HTTP 500"));
    renderProtocol({ onIntegrate, loggedToday: [logEntry({ id: "log-77" })] });

    const card = within(morningSection()).getAllByRole("article")[0];
    fireEvent.click(within(card).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(within(card).getByText(/another go/i)).toBeInTheDocument(),
    );
  });
});
