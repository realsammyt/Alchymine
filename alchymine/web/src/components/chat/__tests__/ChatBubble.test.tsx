/**
 * ChatBubble — component tests.
 *
 * Covers the three render modes (bubble, panel, split) and the systemKey
 * sync that happens on route change via usePageContext.
 */

import { fireEvent, render, screen } from "@testing-library/react";

import { ChatProvider } from "@/contexts/ChatContext";
import ChatBubble from "@/components/chat/ChatBubble";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Stub ChatPanel so we don't drag in the full chat stack.
jest.mock("@/components/chat/ChatPanel", () => {
  return function MockChatPanel({
    systemKey,
  }: {
    systemKey?: string | null;
  }) {
    return (
      <div data-testid="chat-panel">ChatPanel:{systemKey ?? "general"}</div>
    );
  };
});

// Stub usePageContext — returns healing as the active system.
jest.mock("@/hooks/usePageContext", () => ({
  usePageContext: () => ({
    systemKey: "healing",
    systemLabel: "Healing",
    pathname: "/healing",
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderBubble() {
  return render(
    <ChatProvider>
      <ChatBubble />
    </ChatProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ChatBubble", () => {
  it("renders FAB button in bubble mode with no chat panel visible", () => {
    renderBubble();

    // FAB should be present
    expect(
      screen.getByRole("button", { name: /open chat/i }),
    ).toBeInTheDocument();

    // ChatPanel should NOT be rendered in bubble mode
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
  });

  it("clicking FAB opens panel mode and renders ChatPanel", () => {
    renderBubble();

    fireEvent.click(screen.getByRole("button", { name: /open chat/i }));

    // FAB should be gone
    expect(
      screen.queryByRole("button", { name: /open chat/i }),
    ).not.toBeInTheDocument();

    // ChatPanel should appear
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  it("close button returns to bubble mode", () => {
    renderBubble();

    // Open panel first
    fireEvent.click(screen.getByRole("button", { name: /open chat/i }));
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();

    // Close it
    fireEvent.click(screen.getByRole("button", { name: /close/i }));

    // Should be back to bubble
    expect(
      screen.getByRole("button", { name: /open chat/i }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
  });

  it("expand button switches from panel mode to split mode", () => {
    renderBubble();

    // Open panel
    fireEvent.click(screen.getByRole("button", { name: /open chat/i }));

    // In panel mode there should be an Expand button
    const expandBtn = screen.getByRole("button", { name: /expand/i });
    fireEvent.click(expandBtn);

    // After expanding, the header shows a Collapse button (not Expand)
    expect(
      screen.getByRole("button", { name: /collapse/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /expand/i }),
    ).not.toBeInTheDocument();

    // ChatPanel is still visible
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  it("syncs systemKey from usePageContext so ChatPanel receives the route's system", () => {
    renderBubble();

    // Open panel so ChatPanel renders
    fireEvent.click(screen.getByRole("button", { name: /open chat/i }));

    // usePageContext returns { systemKey: "healing" }, so ChatPanel should
    // receive "healing" as its systemKey prop.
    expect(screen.getByTestId("chat-panel")).toHaveTextContent(
      "ChatPanel:healing",
    );
  });
});
