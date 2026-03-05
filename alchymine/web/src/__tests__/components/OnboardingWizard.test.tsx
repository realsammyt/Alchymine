import { render, screen, fireEvent } from "@testing-library/react";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

// Mock framer-motion to avoid animation issues in tests
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
  useReducedMotion: () => true,
}));

// Mock next/link
jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
    onClick,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: () => void;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} onClick={onClick} {...props}>
        {children}
      </a>
    );
  };
});

describe("OnboardingWizard", () => {
  let onComplete: jest.Mock;

  beforeEach(() => {
    onComplete = jest.fn();
    // Clear localStorage mock
    Object.defineProperty(window, "localStorage", {
      value: {
        setItem: jest.fn(),
        getItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
      },
      writable: true,
    });
  });

  it("renders step 1 (Welcome) by default", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    expect(screen.getByText(/Welcome to/)).toBeInTheDocument();
  });

  it("shows all five pillar names on step 1", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    expect(screen.getByText("Personal Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Ethical Healing")).toBeInTheDocument();
    expect(screen.getByText("Generational Wealth")).toBeInTheDocument();
    expect(screen.getByText("Creative Forge")).toBeInTheDocument();
    expect(screen.getByText("Perspective Prism")).toBeInTheDocument();
  });

  it("advances to step 2 when Next is clicked", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByText(/Let's personalize your/)).toBeInTheDocument();
  });

  it("shows name and birth date inputs on step 2", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    expect(screen.getByLabelText("Your name")).toBeInTheDocument();
    expect(screen.getByLabelText("Date of birth")).toBeInTheDocument();
  });

  it("disables Next on step 2 until name and birth date are filled", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    // On step 2 the nav button still says "Next"
    const nextBtn = screen.getByRole("button", { name: "Next" });
    expect(nextBtn).toBeDisabled();
  });

  it("enables Next on step 2 when both fields are filled", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    const nextBtn = screen.getByRole("button", { name: "Next" });
    expect(nextBtn).not.toBeDisabled();
  });

  it("advances to step 3 and shows life path number", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    // Step 1 → Step 2
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    // Step 2 → Step 3
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Your First Insight")).toBeInTheDocument();
    // Life path 5 for 1990-07-15
    expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
  });

  it("shows the user's name on step 3", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Alara")).toBeInTheDocument();
  });

  it("goes back to step 2 from step 3", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByText("Back"));
    expect(screen.getByLabelText("Your name")).toBeInTheDocument();
  });

  it("advances to step 4 (Explore Dashboard) from step 3", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    // Step 3 → Step 4: button says "See Insights"
    fireEvent.click(screen.getByText("See Insights"));
    expect(screen.getByText(/Explore Your/)).toBeInTheDocument();
  });

  it("shows all five pillar Explore links on step 4", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    // Navigate to step 4
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByText("See Insights"));
    // All pillars shown with Explore links
    const exploreLinks = screen.getAllByRole("link");
    expect(exploreLinks.length).toBeGreaterThanOrEqual(5);
  });

  it("calls onComplete when Go to Dashboard is clicked on step 4", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByText("See Insights"));
    fireEvent.click(screen.getByText("Go to Dashboard"));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("sets onboarding_complete in localStorage on completion", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Alara" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1990-07-15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByText("See Insights"));
    fireEvent.click(screen.getByText("Go to Dashboard"));
    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      "onboarding_complete",
      "true",
    );
  });

  it("renders as a dialog with aria-modal", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });

  it("life path number calculation: 1985-11-22 gives master number 11", () => {
    render(<OnboardingWizard onComplete={onComplete} />);
    // Step 1 → Step 2
    fireEvent.click(screen.getByText("Next"));
    fireEvent.change(screen.getByLabelText("Your name"), {
      target: { value: "Test" },
    });
    fireEvent.change(screen.getByLabelText("Date of birth"), {
      target: { value: "1985-11-22" },
    });
    // Step 2 → Step 3 (button says "Next" on step 1)
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    // Now on Step 3 (First Insight), life path 11 should show
    expect(screen.getAllByText("11").length).toBeGreaterThanOrEqual(1);
  });
});
