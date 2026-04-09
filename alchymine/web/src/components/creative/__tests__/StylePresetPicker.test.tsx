import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";

import StylePresetPicker from "@/components/creative/StylePresetPicker";

// Prevent the component's useEffect from hitting the real API.
beforeEach(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [
      { id: "mystical", name: "Mystical", description: "Sacred geometry" },
      { id: "modern", name: "Modern", description: "Clean editorial" },
      { id: "organic", name: "Organic", description: "Botanical watercolour" },
      { id: "celestial", name: "Celestial", description: "Starfields" },
      { id: "grounded", name: "Grounded", description: "Earth tones" },
    ],
  }) as unknown as typeof fetch;
});

afterEach(() => {
  jest.clearAllMocks();
});

describe("StylePresetPicker", () => {
  it("renders all five presets from the API", async () => {
    await act(async () => {
      render(<StylePresetPicker selected={null} onSelect={() => {}} />);
    });

    await waitFor(() => {
      expect(screen.getByTestId("style-preset-mystical")).toBeInTheDocument();
    });
    expect(screen.getByTestId("style-preset-modern")).toBeInTheDocument();
    expect(screen.getByTestId("style-preset-organic")).toBeInTheDocument();
    expect(screen.getByTestId("style-preset-celestial")).toBeInTheDocument();
    expect(screen.getByTestId("style-preset-grounded")).toBeInTheDocument();
  });

  it("falls back to the hardcoded list if the API errors", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }) as unknown as typeof fetch;

    await act(async () => {
      render(<StylePresetPicker selected={null} onSelect={() => {}} />);
    });

    // Fallback should render immediately (no await) since it's seeded
    // into state before the effect runs.
    expect(screen.getByTestId("style-preset-mystical")).toBeInTheDocument();
    expect(screen.getByTestId("style-preset-grounded")).toBeInTheDocument();
  });

  it("invokes onSelect with the preset id when clicked", async () => {
    const onSelect = jest.fn();
    await act(async () => {
      render(<StylePresetPicker selected={null} onSelect={onSelect} />);
    });

    fireEvent.click(screen.getByTestId("style-preset-celestial"));
    expect(onSelect).toHaveBeenCalledWith("celestial");
  });

  it("marks the selected preset with aria-pressed=true", async () => {
    await act(async () => {
      render(<StylePresetPicker selected="modern" onSelect={() => {}} />);
    });

    const selected = screen.getByTestId("style-preset-modern");
    expect(selected).toHaveAttribute("aria-pressed", "true");
    const other = screen.getByTestId("style-preset-mystical");
    expect(other).toHaveAttribute("aria-pressed", "false");
  });

  it("supports keyboard navigation: arrow keys move focus, Enter selects", async () => {
    const onSelect = jest.fn();
    await act(async () => {
      render(<StylePresetPicker selected={null} onSelect={onSelect} />);
    });

    const firstCard = screen.getByTestId("style-preset-mystical");
    firstCard.focus();
    expect(document.activeElement).toBe(firstCard);

    fireEvent.keyDown(firstCard, { key: "ArrowRight" });
    const secondCard = screen.getByTestId("style-preset-modern");
    expect(document.activeElement).toBe(secondCard);

    fireEvent.keyDown(secondCard, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("modern");
  });

  it("shows the matched badge when a creative profile is provided", async () => {
    await act(async () => {
      render(
        <StylePresetPicker
          selected={null}
          onSelect={() => {}}
          creativeProfile={{ creative_orientation: "The Architect" }}
        />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("style-preset-modern")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("style-preset-modern-badge"),
    ).toBeInTheDocument();
  });
});
