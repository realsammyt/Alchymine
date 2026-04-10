/**
 * ChatSearch — component tests.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ChatSearch from "@/components/chat/ChatSearch";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock("@/lib/chat", () => ({
  fetchChatHistory: jest.fn().mockResolvedValue([
    { id: "1", role: "user", content: "breathwork tips", createdAt: "2026-04-10T00:00:00Z" },
    { id: "2", role: "assistant", content: "Try 4-7-8 breathing", createdAt: "2026-04-10T00:00:01Z" },
  ]),
  streamChat: jest.fn(),
}));

// ---------------------------------------------------------------------------
// Import after mock so we can spy on the mock
// ---------------------------------------------------------------------------

import { fetchChatHistory } from "@/lib/chat";

const mockFetchChatHistory = fetchChatHistory as jest.MockedFunction<
  typeof fetchChatHistory
>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderSearch(systemKey: string | null = "healing") {
  const onClose = jest.fn();
  const utils = render(
    <ChatSearch systemKey={systemKey} onClose={onClose} />,
  );
  return { ...utils, onClose };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChatSearch", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders history and quick-ask tabs", () => {
    renderSearch();

    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(2);

    const labels = tabs.map((t) => t.textContent?.toLowerCase());
    expect(labels).toContain("history");
    expect(labels).toContain("quick ask");
  });

  it("history tab shows search input with correct placeholder", () => {
    renderSearch();

    const input = screen.getByPlaceholderText(/search/i);
    expect(input).toBeInTheDocument();
  });

  it("switching to quick-ask tab shows ask input", () => {
    renderSearch();

    // Click quick ask tab
    const tabs = screen.getAllByRole("tab");
    const quickAskTab = tabs.find((t) =>
      /quick ask/i.test(t.textContent ?? ""),
    )!;
    fireEvent.click(quickAskTab);

    const input = screen.getByPlaceholderText(/ask anything/i);
    expect(input).toBeInTheDocument();
  });

  it("searching history calls fetchChatHistory with q param", async () => {
    renderSearch("healing");

    // Change search input value and submit
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "breathwork" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(mockFetchChatHistory).toHaveBeenCalledWith(
        "healing",
        20,
        "breathwork",
      );
    });
  });
});
