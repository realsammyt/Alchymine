import { render, screen, fireEvent } from "@testing-library/react";
import MethodologyPanel from "@/components/shared/MethodologyPanel";

describe("MethodologyPanel", () => {
  const defaultProps = {
    title: "Test Methodology",
    methodology: "This is how the test methodology works.",
    evidenceLevel: "strong" as const,
    calculationType: "deterministic" as const,
    sources: ["Source 1", "Source 2"],
  };

  it("renders without crashing", () => {
    render(<MethodologyPanel {...defaultProps} />);
    expect(screen.getByText(/Test Methodology/)).toBeInTheDocument();
  });

  it("is collapsed by default", () => {
    render(<MethodologyPanel {...defaultProps} />);
    expect(
      screen.queryByText("This is how the test methodology works."),
    ).not.toBeInTheDocument();
  });

  it("expands when the toggle button is clicked", () => {
    render(<MethodologyPanel {...defaultProps} />);
    const toggleButton = screen.getByRole("button");
    fireEvent.click(toggleButton);
    expect(
      screen.getByText("This is how the test methodology works."),
    ).toBeInTheDocument();
  });

  it("collapses when toggled again", () => {
    render(<MethodologyPanel {...defaultProps} />);
    const toggleButton = screen.getByRole("button");
    // Expand
    fireEvent.click(toggleButton);
    expect(
      screen.getByText("This is how the test methodology works."),
    ).toBeInTheDocument();
    // Collapse
    fireEvent.click(toggleButton);
    expect(
      screen.queryByText("This is how the test methodology works."),
    ).not.toBeInTheDocument();
  });

  it("renders expanded when defaultExpanded is true", () => {
    render(<MethodologyPanel {...defaultProps} defaultExpanded />);
    expect(
      screen.getByText("This is how the test methodology works."),
    ).toBeInTheDocument();
  });

  it("shows evidence rating badge when expanded", () => {
    render(<MethodologyPanel {...defaultProps} defaultExpanded />);
    expect(screen.getByText("Strong Evidence")).toBeInTheDocument();
  });

  it("shows calculation type badge when expanded", () => {
    render(<MethodologyPanel {...defaultProps} defaultExpanded />);
    expect(screen.getByText("Deterministic")).toBeInTheDocument();
  });

  it("shows sources when expanded", () => {
    render(<MethodologyPanel {...defaultProps} defaultExpanded />);
    expect(screen.getByText("Source 1")).toBeInTheDocument();
    expect(screen.getByText("Source 2")).toBeInTheDocument();
  });

  it("has correct aria-expanded attribute", () => {
    render(<MethodologyPanel {...defaultProps} />);
    const toggleButton = screen.getByRole("button");
    expect(toggleButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggleButton);
    expect(toggleButton).toHaveAttribute("aria-expanded", "true");
  });

  it("renders ai-assisted calculation type correctly", () => {
    render(
      <MethodologyPanel
        {...defaultProps}
        calculationType="ai-assisted"
        defaultExpanded
      />,
    );
    expect(screen.getByText("AI-Assisted")).toBeInTheDocument();
  });

  it("renders hybrid calculation type correctly", () => {
    render(
      <MethodologyPanel
        {...defaultProps}
        calculationType="hybrid"
        defaultExpanded
      />,
    );
    expect(screen.getByText("Hybrid")).toBeInTheDocument();
  });
});
