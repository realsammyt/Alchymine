import { render, screen } from "@testing-library/react";
import QualityGateDisplay from "@/components/shared/QualityGateDisplay";

describe("QualityGateDisplay", () => {
  it("renders without crashing", () => {
    render(<QualityGateDisplay checksPassed={5} checksTotal={5} />);
    expect(screen.getByTestId("quality-gate-display")).toBeInTheDocument();
  });

  it("shows verified count in the summary", () => {
    render(<QualityGateDisplay checksPassed={4} checksTotal={5} />);
    const display = screen.getByTestId("quality-gate-display");
    expect(display).toHaveTextContent("4/5");
  });

  it("shows all 5 passed with correct text", () => {
    render(<QualityGateDisplay checksPassed={5} checksTotal={5} />);
    expect(screen.getByText(/quality checks passed/i)).toBeInTheDocument();
    expect(screen.getByText("5/5")).toBeInTheDocument();
  });

  it("renders default quality checks by name", () => {
    render(<QualityGateDisplay checksPassed={5} checksTotal={5} />);
    expect(screen.getByText("Ethics")).toBeInTheDocument();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Completeness")).toBeInTheDocument();
    expect(screen.getByText("Safety")).toBeInTheDocument();
    expect(screen.getByText("Bias")).toBeInTheDocument();
  });

  it("renders custom checks when provided", () => {
    const customChecks = [
      { name: "Custom Check", passed: true },
      { name: "Another Check", passed: false },
    ];
    render(
      <QualityGateDisplay
        checksPassed={1}
        checksTotal={2}
        checks={customChecks}
      />,
    );
    expect(screen.getByText("Custom Check")).toBeInTheDocument();
    expect(screen.getByText("Another Check")).toBeInTheDocument();
  });

  it("has accessible aria-label on the summary", () => {
    render(<QualityGateDisplay checksPassed={5} checksTotal={5} />);
    const summary = screen.getByText(/quality checks passed/i).closest("span");
    expect(summary).toHaveAttribute(
      "aria-label",
      "Verified: 5 of 5 quality checks passed",
    );
  });

  it("renders the checks list with role=list", () => {
    render(<QualityGateDisplay checksPassed={5} checksTotal={5} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });
});
