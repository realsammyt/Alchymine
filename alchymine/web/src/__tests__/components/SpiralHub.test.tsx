import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SpiralHub from "@/components/spiral/SpiralHub";

// Mock next/link
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

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("SpiralHub", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("renders without crashing", () => {
    render(<SpiralHub />);
    expect(screen.getByText("The Alchemical Spiral")).toBeInTheDocument();
  });

  it("displays the guided intention prompts", () => {
    render(<SpiralHub />);
    expect(
      screen.getByText("I want to understand myself better"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I need to make a financial decision"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I'm feeling stuck creatively"),
    ).toBeInTheDocument();
    expect(screen.getByText("I want to heal emotionally")).toBeInTheDocument();
    expect(screen.getByText("I need career direction")).toBeInTheDocument();
    expect(
      screen.getByText("I want to build generational wealth"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I want to see things differently"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I want to improve my relationships"),
    ).toBeInTheDocument();
    expect(screen.getByText("I want to find my purpose")).toBeInTheDocument();
    expect(
      screen.getByText("I want to build a lasting legacy"),
    ).toBeInTheDocument();
  });

  it("renders all 10 intention buttons", () => {
    render(<SpiralHub />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBe(10);
  });

  it("shows loading state when an intention is clicked", async () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    primary_system: "intelligence",
                    recommendations: [],
                    for_you_today: "Test message",
                    evidence_level: "strong",
                    calculation_type: "deterministic",
                    methodology: "Test methodology",
                  }),
              }),
            500,
          ),
        ),
    );

    render(<SpiralHub />);
    const button = screen.getByText("I want to understand myself better");
    fireEvent.click(button);

    expect(
      screen.getByText("Calculating your optimal path..."),
    ).toBeInTheDocument();
  });

  it("displays recommendations after successful API call", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          primary_system: "intelligence",
          recommendations: [
            {
              system: "intelligence",
              score: 92,
              reason: "Your profile aligns with deep self-exploration.",
              entry_action: "Start your numerology reading",
              priority: 1,
            },
            {
              system: "healing",
              score: 75,
              reason: "Emotional healing supports self-understanding.",
              entry_action: "Begin a breathwork session",
              priority: 2,
            },
          ],
          for_you_today: "Today is about understanding your inner world.",
          evidence_level: "strong",
          calculation_type: "deterministic",
          methodology: "Spiral routing methodology",
        }),
    });

    render(<SpiralHub />);
    fireEvent.click(screen.getByText("I want to understand myself better"));

    await waitFor(() => {
      expect(
        screen.getByText("Today is about understanding your inner world."),
      ).toBeInTheDocument();
    });

    expect(screen.getByText("Personalized Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Ethical Healing")).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("Best Match")).toBeInTheDocument();
  });

  it("displays error state on API failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<SpiralHub />);
    fireEvent.click(screen.getByText("I want to understand myself better"));

    await waitFor(() => {
      expect(screen.getByText("HTTP 500")).toBeInTheDocument();
    });
  });

  it("sets aria-pressed on selected intention", () => {
    mockFetch.mockImplementation(
      () => new Promise(() => {}), // never resolves
    );

    render(<SpiralHub />);
    const button = screen.getByTestId("intention-self-understanding");
    expect(button).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
  });

  it("renders the spiral visual", () => {
    render(<SpiralHub />);
    // The spiral visual container should be present
    const container = document.querySelector(".spiral-visual-container");
    expect(container).toBeInTheDocument();
  });

  it("renders recommendation cards with links to system pages", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          primary_system: "wealth",
          recommendations: [
            {
              system: "wealth",
              score: 88,
              reason: "Financial focus detected.",
              entry_action: "Review your plan",
              priority: 1,
            },
          ],
          for_you_today: "Focus on your finances today.",
          evidence_level: "strong",
          calculation_type: "deterministic",
          methodology: "Test",
        }),
    });

    render(<SpiralHub />);
    fireEvent.click(screen.getByText("I need to make a financial decision"));

    await waitFor(() => {
      expect(screen.getByText("Generational Wealth")).toBeInTheDocument();
    });

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/wealth");
  });
});
