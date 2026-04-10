import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import JournalEntryActions from "../JournalEntryActions";
import { JournalEntry } from "@/lib/api";

// ── Mock the API module ──────────────────────────────────────────────

jest.mock("@/lib/api", () => ({
  updateJournalEntry: jest.fn(() =>
    Promise.resolve({
      ...mockEntry,
      title: "Updated Title",
      content: "Updated Content",
    }),
  ),
  deleteJournalEntry: jest.fn(() => Promise.resolve()),
}));

const { updateJournalEntry, deleteJournalEntry } =
  jest.requireMock("@/lib/api");

// ── Test data ────────────────────────────────────────────────────────

const mockEntry: JournalEntry = {
  id: "entry-123",
  user_id: "user-456",
  system: "healing",
  entry_type: "practice-log",
  title: "Morning Breathwork",
  content: "Completed 8 cycles of box breathing today.",
  tags: ["breathwork", "morning"],
  mood_score: 7,
  created_at: "2026-04-08T09:00:00Z",
  updated_at: "2026-04-08T09:00:00Z",
};

// ── Tests ────────────────────────────────────────────────────────────

describe("JournalEntryActions", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders the entry in view mode with edit/delete buttons", () => {
    render(<JournalEntryActions entry={mockEntry} />);

    expect(screen.getByText("Morning Breathwork")).toBeInTheDocument();
    expect(
      screen.getByText("Completed 8 cycles of box breathing today."),
    ).toBeInTheDocument();
    expect(screen.getByText("Mood: 7/10")).toBeInTheDocument();
    expect(screen.getByText("breathwork")).toBeInTheDocument();
    expect(screen.getByText("morning")).toBeInTheDocument();
    expect(screen.getByTestId("journal-edit-btn")).toBeInTheDocument();
    expect(screen.getByTestId("journal-delete-btn")).toBeInTheDocument();
  });

  it("shows edit form when Edit is clicked", () => {
    render(<JournalEntryActions entry={mockEntry} />);
    fireEvent.click(screen.getByTestId("journal-edit-btn"));

    expect(screen.getByTestId("journal-edit-form")).toBeInTheDocument();
    expect(screen.getByTestId("journal-edit-title")).toHaveValue(
      "Morning Breathwork",
    );
    expect(screen.getByTestId("journal-edit-content")).toHaveValue(
      "Completed 8 cycles of box breathing today.",
    );
    expect(screen.getByTestId("journal-edit-mood")).toHaveValue(7);
  });

  it("calls updateJournalEntry on save and invokes onUpdated", async () => {
    const onUpdated = jest.fn();
    render(<JournalEntryActions entry={mockEntry} onUpdated={onUpdated} />);

    fireEvent.click(screen.getByTestId("journal-edit-btn"));

    // Modify the title
    fireEvent.change(screen.getByTestId("journal-edit-title"), {
      target: { value: "Updated Title" },
    });

    fireEvent.click(screen.getByTestId("journal-save-btn"));

    await waitFor(() => {
      expect(updateJournalEntry).toHaveBeenCalledWith("entry-123", {
        title: "Updated Title",
        content: "Completed 8 cycles of box breathing today.",
        mood_score: 7,
      });
    });

    await waitFor(() => {
      expect(onUpdated).toHaveBeenCalled();
    });
  });

  it("returns to view mode on Cancel in edit form", () => {
    render(<JournalEntryActions entry={mockEntry} />);
    fireEvent.click(screen.getByTestId("journal-edit-btn"));

    expect(screen.getByTestId("journal-edit-form")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.getByTestId("journal-entry-actions")).toBeInTheDocument();
  });

  it("shows delete confirmation when Delete is clicked", () => {
    render(<JournalEntryActions entry={mockEntry} />);
    fireEvent.click(screen.getByTestId("journal-delete-btn"));

    expect(screen.getByTestId("journal-delete-confirm")).toBeInTheDocument();
    expect(
      screen.getByText("Delete this journal entry?"),
    ).toBeInTheDocument();
  });

  it("calls deleteJournalEntry on confirm and invokes onDeleted", async () => {
    const onDeleted = jest.fn();
    render(<JournalEntryActions entry={mockEntry} onDeleted={onDeleted} />);

    fireEvent.click(screen.getByTestId("journal-delete-btn"));
    fireEvent.click(screen.getByTestId("journal-confirm-delete-btn"));

    await waitFor(() => {
      expect(deleteJournalEntry).toHaveBeenCalledWith("entry-123");
    });

    await waitFor(() => {
      expect(onDeleted).toHaveBeenCalledWith("entry-123");
    });
  });

  it("returns to view mode when Cancel is clicked on delete confirmation", () => {
    render(<JournalEntryActions entry={mockEntry} />);
    fireEvent.click(screen.getByTestId("journal-delete-btn"));

    expect(screen.getByTestId("journal-delete-confirm")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.getByTestId("journal-entry-actions")).toBeInTheDocument();
  });

  it("handles entry without mood_score gracefully", () => {
    const noMoodEntry = { ...mockEntry, mood_score: null };
    render(<JournalEntryActions entry={noMoodEntry} />);

    expect(screen.queryByText(/Mood:/)).not.toBeInTheDocument();
  });

  it("handles entry without tags gracefully", () => {
    const noTagsEntry = { ...mockEntry, tags: [] };
    render(<JournalEntryActions entry={noTagsEntry} />);

    // No tag elements rendered
    expect(screen.queryByText("breathwork")).not.toBeInTheDocument();
  });
});
