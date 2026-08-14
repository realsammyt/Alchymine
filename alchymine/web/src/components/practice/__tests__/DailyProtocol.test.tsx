import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import DailyProtocol from "../DailyProtocol";
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

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    expect(within(card).getByText("Done today.")).toBeInTheDocument();

    release(logEntry());
    await waitFor(() => expect(onLog).toHaveBeenCalled());
  });

  it("posts the slot and the local day with the completion", async () => {
    const { props } = renderProtocol();

    const card = within(morningSection()).getAllByRole("group")[0];
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

    const card = within(morningSection()).getAllByRole("group")[0];
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

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() => expect(props.onLogged).toHaveBeenCalled());
  });

  it("does not fire onLogged when the write failed", async () => {
    const onLog = jest.fn().mockRejectedValue(new Error("HTTP 500"));
    const { props } = renderProtocol({ onLog });

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() => expect(onLog).toHaveBeenCalled());
    expect(props.onLogged).not.toHaveBeenCalled();
  });

  it("completes one slot without touching the same practice elsewhere", async () => {
    renderProtocol();

    const morningCard = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(
      within(morningCard).getByRole("button", { name: /done/i }),
    );

    const eveningCard = within(
      screen.getByRole("region", { name: /evening/i }),
    ).getAllByRole("group")[0];
    expect(
      within(eveningCard).queryByText("Done today."),
    ).not.toBeInTheDocument();
  });
});

describe("DailyProtocol skipping", () => {
  it("writes a skipped row with no penalty copy", async () => {
    const { props, container } = renderProtocol();

    const card = within(morningSection()).getAllByRole("group")[0];
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

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(
        within(card).getByText(FLOOR_DEFINITION.self_check.question),
      ).toBeInTheDocument(),
    );
  });

  it("offers the integration prompt after a completion", async () => {
    renderProtocol();

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(
        within(card).getByRole("link", { name: /journal/i }),
      ).toBeInTheDocument(),
    );
  });

  it("posts the integration against the practice log row that was created", async () => {
    const { props } = renderProtocol({
      onLog: jest.fn().mockResolvedValue(logEntry({ id: "log-99" })),
    });

    const card = within(morningSection()).getAllByRole("group")[0];
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

  it("shows no self-check when the definition is not loaded", async () => {
    renderProtocol({ lookup: () => undefined });

    const card = within(morningSection()).getAllByRole("group")[0];
    fireEvent.click(within(card).getByRole("button", { name: /done/i }));

    await waitFor(() =>
      expect(within(card).getByText("Done today.")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(FLOOR_DEFINITION.self_check.question),
    ).not.toBeInTheDocument();
  });
});
