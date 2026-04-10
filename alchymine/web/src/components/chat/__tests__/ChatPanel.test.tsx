/**
 * ChatPanel — component tests.
 *
 * Mocks ``useChat`` so we can drive the rendering states directly:
 * empty, messages present, error visible/dismissable, and starter
 * prompt chip clicks.
 */

import { fireEvent, render, screen } from "@testing-library/react";

import ChatPanel from "@/components/chat/ChatPanel";
import type { ChatMessage } from "@/lib/chat";

// Mock react-markdown because jest+ESM interop blows up on the real
// module in jsdom without extra config.  The component under test
// only cares that assistant content is displayed.
jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => (
    <div data-testid="md">{children}</div>
  ),
}));

type UseChatValue = {
  messages: ChatMessage[];
  isStreaming: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  sendMessage: jest.Mock;
  cancelStream: jest.Mock;
  resetConversation: jest.Mock;
};

const useChatMock = jest.fn<UseChatValue, []>();

jest.mock("@/hooks/useChat", () => ({
  useChat: () => useChatMock(),
}));

beforeEach(() => {
  useChatMock.mockReset();
});

function defaults(overrides: Partial<UseChatValue> = {}): UseChatValue {
  return {
    messages: [],
    isStreaming: false,
    isLoadingHistory: false,
    error: null,
    sendMessage: jest.fn(),
    cancelStream: jest.fn(),
    resetConversation: jest.fn(),
    ...overrides,
  };
}

describe("ChatPanel", () => {
  it("renders the welcome empty state when there are no messages", () => {
    useChatMock.mockReturnValue(defaults());
    render(<ChatPanel systemKey={null} />);

    expect(
      screen.getByRole("heading", { name: /growth assistant/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/welcome to your growth assistant/i)).toBeInTheDocument();
    // No "New conversation" button yet.
    expect(
      screen.queryByRole("button", { name: /new conversation/i }),
    ).not.toBeInTheDocument();
  });

  it("renders user and assistant messages and a reset button", () => {
    useChatMock.mockReturnValue(
      defaults({
        messages: [
          {
            id: "u1",
            role: "user",
            content: "Hi coach",
            createdAt: "2026-04-09T00:00:00.000Z",
          },
          {
            id: "a1",
            role: "assistant",
            content: "Hello **friend**",
            createdAt: "2026-04-09T00:00:00.100Z",
          },
        ],
      }),
    );

    render(<ChatPanel systemKey="healing" />);
    expect(screen.getByText(/ethical healing specialist/i)).toBeInTheDocument();
    expect(screen.getByText("Hi coach")).toBeInTheDocument();
    // Markdown mock passes the raw string through a data-testid wrapper.
    expect(screen.getByTestId("md")).toHaveTextContent("Hello **friend**");
    expect(
      screen.getByRole("button", { name: /new conversation/i }),
    ).toBeInTheDocument();
  });

  it("shows an error banner when error is set and dismisses it on click", () => {
    useChatMock.mockReturnValue(
      defaults({
        error: "Content flagged by safety filter",
        messages: [
          {
            id: "u1",
            role: "user",
            content: "bad input",
            createdAt: "2026-04-09T00:00:00.000Z",
          },
        ],
      }),
    );

    render(<ChatPanel systemKey={null} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/safety filter/i);

    fireEvent.click(screen.getByRole("button", { name: /dismiss error/i }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("calls sendMessage via the ChatInput with the trimmed value", () => {
    const sendMessage = jest.fn();
    useChatMock.mockReturnValue(defaults({ sendMessage }));

    render(<ChatPanel systemKey="wealth" />);
    const textarea = screen.getByLabelText(/chat message/i);
    fireEvent.change(textarea, { target: { value: "  hello  " } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(sendMessage).toHaveBeenCalledTimes(1);
    expect(sendMessage).toHaveBeenCalledWith("hello", "wealth");
  });

  it("renders starter prompt chips when empty and not loading history", () => {
    useChatMock.mockReturnValue(defaults());
    render(<ChatPanel systemKey="healing" />);

    // Healing system should show its 3 starter prompts.
    expect(screen.getByText("Breathwork for me")).toBeInTheDocument();
    expect(screen.getByText("My healing journey")).toBeInTheDocument();
    expect(screen.getByText("Shadow work guide")).toBeInTheDocument();
  });

  it("renders general starter prompts when systemKey is null", () => {
    useChatMock.mockReturnValue(defaults());
    render(<ChatPanel systemKey={null} />);

    expect(screen.getByText("Start my journey")).toBeInTheDocument();
    expect(screen.getByText("Explore my profile")).toBeInTheDocument();
    expect(screen.getByText("Daily check-in")).toBeInTheDocument();
  });

  it("sends the starter prompt message when a chip is clicked", () => {
    const sendMessage = jest.fn();
    useChatMock.mockReturnValue(defaults({ sendMessage }));

    render(<ChatPanel systemKey="wealth" />);
    fireEvent.click(screen.getByText("Budget approach"));

    expect(sendMessage).toHaveBeenCalledTimes(1);
    expect(sendMessage).toHaveBeenCalledWith(
      "Review my budget approach and suggest improvements based on my profile.",
      "wealth",
    );
  });

  it("hides starter prompts while history is loading", () => {
    useChatMock.mockReturnValue(defaults({ isLoadingHistory: true }));
    render(<ChatPanel systemKey="healing" />);

    expect(screen.queryByText("Breathwork for me")).not.toBeInTheDocument();
    expect(
      screen.getByText(/loading your conversation history/i),
    ).toBeInTheDocument();
  });

  it("hides starter prompts when messages exist", () => {
    useChatMock.mockReturnValue(
      defaults({
        messages: [
          {
            id: "u1",
            role: "user",
            content: "Hey",
            createdAt: "2026-04-09T00:00:00.000Z",
          },
        ],
      }),
    );

    render(<ChatPanel systemKey="healing" />);
    expect(screen.queryByText("Breathwork for me")).not.toBeInTheDocument();
  });
});
