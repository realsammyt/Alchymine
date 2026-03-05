import { render, screen, fireEvent } from "@testing-library/react";
import ContextualGuide from "@/components/shared/ContextualGuide";
import { COPY } from "@/lib/copy";

// Mock framer-motion to avoid animation complexity in tests
jest.mock("framer-motion", () => ({
  motion: {
    div: ({
      children,
      ...props
    }: {
      children: React.ReactNode;
      [key: string]: unknown;
    }) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "localStorage", {
  value: localStorageMock,
  writable: true,
});

describe("ContextualGuide", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it("renders the correct pillar intro text for intelligence", () => {
    render(<ContextualGuide pillar="intelligence" storageKey="intelligence" />);
    expect(
      screen.getByText(COPY.pillarIntros.intelligence),
    ).toBeInTheDocument();
  });

  it("renders the correct pillar intro text for healing", () => {
    render(<ContextualGuide pillar="healing" storageKey="healing" />);
    expect(screen.getByText(COPY.pillarIntros.healing)).toBeInTheDocument();
  });

  it("renders the correct pillar intro text for wealth", () => {
    render(<ContextualGuide pillar="wealth" storageKey="wealth" />);
    expect(screen.getByText(COPY.pillarIntros.wealth)).toBeInTheDocument();
  });

  it("renders the correct pillar intro text for creative", () => {
    render(<ContextualGuide pillar="creative" storageKey="creative" />);
    expect(screen.getByText(COPY.pillarIntros.creative)).toBeInTheDocument();
  });

  it("renders the correct pillar intro text for perspective", () => {
    render(<ContextualGuide pillar="perspective" storageKey="perspective" />);
    expect(screen.getByText(COPY.pillarIntros.perspective)).toBeInTheDocument();
  });

  it("shows a dismiss button with label 'Got it'", () => {
    render(<ContextualGuide pillar="healing" storageKey="healing" />);
    expect(screen.getByText("Got it")).toBeInTheDocument();
  });

  it("hides the guide after clicking 'Got it'", () => {
    render(<ContextualGuide pillar="healing" storageKey="healing" />);
    const button = screen.getByText("Got it");
    fireEvent.click(button);
    expect(
      screen.queryByText(COPY.pillarIntros.healing),
    ).not.toBeInTheDocument();
  });

  it("persists dismissal to localStorage with correct key", () => {
    render(<ContextualGuide pillar="wealth" storageKey="wealth" />);
    fireEvent.click(screen.getByText("Got it"));
    expect(localStorageMock.getItem("guide_dismissed_wealth")).toBe("true");
  });

  it("does not render when localStorage has the dismissed key", () => {
    localStorageMock.setItem("guide_dismissed_perspective", "true");
    render(<ContextualGuide pillar="perspective" storageKey="perspective" />);
    expect(
      screen.queryByText(COPY.pillarIntros.perspective),
    ).not.toBeInTheDocument();
  });

  it("uses the storageKey prop as part of the localStorage key", () => {
    localStorageMock.setItem("guide_dismissed_custom-key", "true");
    render(<ContextualGuide pillar="creative" storageKey="custom-key" />);
    expect(
      screen.queryByText(COPY.pillarIntros.creative),
    ).not.toBeInTheDocument();
  });
});
