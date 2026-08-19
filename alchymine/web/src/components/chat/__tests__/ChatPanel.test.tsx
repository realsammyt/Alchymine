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
import { PlanGateError } from "@/lib/planGate";

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
  upsell: PlanGateError | null;
  sendMessage: jest.Mock;
  retryLastTurn: jest.Mock;
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
    upsell: null,
    sendMessage: jest.fn(),
    retryLastTurn: jest.fn(),
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

  describe("plan upsell banner", () => {
    const upsell = new PlanGateError(
      "plan_allowance_reached",
      "You've used this month's included coaching. Upgrade to keep going.",
      new Date("2026-09-01T00:00:00Z"),
      "pro",
      "/pricing",
    );

    it("renders a spent allowance as a status, not an alert", () => {
      // Nothing is broken. Dressing a sales moment as a fault trains
      // people to ignore real faults.
      useChatMock.mockReturnValue(defaults({ upsell }));
      render(<ChatPanel systemKey={null} />);

      expect(screen.getByRole("status")).toHaveTextContent(
        /included coaching/i,
      );
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("offers somewhere to go and says when it resets", () => {
      useChatMock.mockReturnValue(defaults({ upsell }));
      render(<ChatPanel systemKey={null} />);

      expect(screen.getByRole("link", { name: /see plans/i })).toHaveAttribute(
        "href",
        "/pricing",
      );
      expect(screen.getByText(/Resets on September 1/)).toBeInTheDocument();
    });

    it("shows nothing when the plan is fine", () => {
      useChatMock.mockReturnValue(defaults());
      render(<ChatPanel systemKey={null} />);

      expect(screen.queryByRole("link", { name: /see plans/i })).not.toBeInTheDocument();
    });

    it("renders for the practice scope too", () => {
      // The sixth scope goes through the same metered path, so a refusal
      // has to read the same way there as everywhere else.
      useChatMock.mockReturnValue(defaults({ upsell }));
      render(<ChatPanel systemKey="practice" />);

      expect(screen.getByRole("status")).toHaveTextContent(
        /included coaching/i,
      );
      expect(screen.getByRole("link", { name: /see plans/i })).toBeInTheDocument();
    });

    it("keeps the red error banner for actual faults", () => {
      useChatMock.mockReturnValue(defaults({ error: "Streaming failed" }));
      render(<ChatPanel systemKey={null} />);

      expect(screen.getByRole("alert")).toHaveTextContent("Streaming failed");
    });
  });
});

/**
 * Issue #297. A reply that lost its connection used to render exactly
 * like a finished one. The bubble now says so where the text is, quietly
 * enough that it does not read as a fault, and offers the one thing that
 * helps: asking again.
 */
describe("ChatPanel interrupted replies", () => {
  const cutOff: ChatMessage[] = [
    { id: "u1", role: "user", content: "What next?", createdAt: "2026-08-19T10:00:00Z" },
    {
      id: "a1",
      role: "assistant",
      content: "Start by",
      createdAt: "2026-08-19T10:00:01Z",
      interrupted: true,
    },
  ];

  it("says the reply may be incomplete", () => {
    useChatMock.mockReturnValue(defaults({ messages: cutOff }));
    render(<ChatPanel systemKey={null} />);

    expect(screen.getByText(/may be incomplete/i)).toBeInTheDocument();
  });

  it("reads as a status rather than an alert", () => {
    // Nothing is broken and nobody needs interrupting: the connection
    // ended, and the text on screen is still the user's to read.
    useChatMock.mockReturnValue(defaults({ messages: cutOff }));
    render(<ChatPanel systemKey={null} />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/may be incomplete/i);
  });

  it("offers to ask again, and asks again when clicked", () => {
    const retryLastTurn = jest.fn();
    useChatMock.mockReturnValue(defaults({ messages: cutOff, retryLastTurn }));
    render(<ChatPanel systemKey={null} />);

    fireEvent.click(screen.getByRole("button", { name: /ask again/i }));

    expect(retryLastTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps the partial text on screen", () => {
    useChatMock.mockReturnValue(defaults({ messages: cutOff }));
    render(<ChatPanel systemKey={null} />);

    expect(screen.getByTestId("md")).toHaveTextContent("Start by");
  });

  it("says nothing about a reply that finished", () => {
    useChatMock.mockReturnValue(
      defaults({
        messages: [
          { ...cutOff[0] },
          { ...cutOff[1], content: "Start by breathing.", interrupted: false },
        ],
      }),
    );
    render(<ChatPanel systemKey={null} />);

    expect(screen.queryByText(/may be incomplete/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ask again/i })).not.toBeInTheDocument();
  });

  it("offers the retry on the newest reply only", () => {
    // Retrying re-sends the *last* message, so offering the button on an
    // older bubble would answer a different question than the one it sits
    // under. The note stays; only the affordance is scoped.
    useChatMock.mockReturnValue(
      defaults({
        messages: [
          ...cutOff,
          { id: "u2", role: "user", content: "And then?", createdAt: "2026-08-19T10:01:00Z" },
          {
            id: "a2",
            role: "assistant",
            content: "Then rest.",
            createdAt: "2026-08-19T10:01:01Z",
          },
        ],
      }),
    );
    render(<ChatPanel systemKey={null} />);

    expect(screen.getByText(/may be incomplete/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ask again/i })).not.toBeInTheDocument();
  });

  it("hides the retry while another reply is streaming", () => {
    useChatMock.mockReturnValue(defaults({ messages: cutOff, isStreaming: true }));
    render(<ChatPanel systemKey={null} />);

    expect(screen.queryByRole("button", { name: /ask again/i })).not.toBeInTheDocument();
  });
});
