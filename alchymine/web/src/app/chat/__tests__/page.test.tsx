/**
 * /chat page — deep-link scope tests.
 *
 * The page's one job is turning `?system=<key>` into the scope it hands
 * to ChatPanel, so ChatPanel is stubbed and the resolved prop is read
 * straight off the rendered output.  Every key the backend accepts gets
 * a case here: a scope that resolves in `usePageContext` but not on this
 * page is the exact bug this file guards against (#285).
 */

import { render, screen } from "@testing-library/react";

import ChatPage from "../page";
import { SYSTEM_KEYS } from "@/hooks/usePageContext";

const mockSearchParams = jest.fn<URLSearchParams, []>();

jest.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams(),
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

// Stubbed so the assertions read the resolved scope directly instead of
// going through ChatPanel's own rendering, which has its own tests.
jest.mock("@/components/chat/ChatPanel", () => ({
  __esModule: true,
  default: ({
    systemKey,
    initialPrompt,
  }: {
    systemKey?: string | null;
    initialPrompt?: string;
  }) => (
    <div
      data-testid="chat-panel"
      data-system-key={systemKey ?? "general"}
      data-initial-prompt={initialPrompt ?? ""}
    />
  ),
}));

function renderChatPage(query: string): HTMLElement {
  mockSearchParams.mockReturnValue(new URLSearchParams(query));
  render(<ChatPage />);
  return screen.getByTestId("chat-panel");
}

beforeEach(() => {
  mockSearchParams.mockReset();
});

describe("ChatPage deep-link scopes", () => {
  it.each([...SYSTEM_KEYS])("opens ?system=%s in that scope", (key) => {
    expect(renderChatPage(`system=${key}`)).toHaveAttribute(
      "data-system-key",
      key,
    );
  });

  it("covers every scope the shared enumeration declares", () => {
    expect([...SYSTEM_KEYS]).toEqual([
      "intelligence",
      "healing",
      "wealth",
      "creative",
      "perspective",
      "practice",
    ]);
  });

  it.each(["astrology", "PRACTICE", "", "../healing"])(
    "falls back to general coaching for ?system=%s",
    (key) => {
      expect(renderChatPage(`system=${key}`)).toHaveAttribute(
        "data-system-key",
        "general",
      );
    },
  );

  it("falls back to general coaching when no system is given", () => {
    expect(renderChatPage("")).toHaveAttribute("data-system-key", "general");
  });

  it("passes the prompt param through alongside the scope", () => {
    const panel = renderChatPage("system=practice&prompt=How+do+I+start");
    expect(panel).toHaveAttribute("data-system-key", "practice");
    expect(panel).toHaveAttribute("data-initial-prompt", "How do I start");
  });
});
