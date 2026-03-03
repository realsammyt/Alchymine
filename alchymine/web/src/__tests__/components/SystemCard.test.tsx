import { render, screen } from "@testing-library/react";
import SystemCard from "@/components/shared/SystemCard";

describe("SystemCard", () => {
  const defaultProps = {
    name: "Test System",
    href: "/test",
    icon: <span>T</span>,
    description: "A test system for testing purposes.",
    status: "active" as const,
    features: ["Feature 1", "Feature 2", "Feature 3"],
    gradient: "from-primary-dark/30 to-primary/20",
  };

  it("renders without crashing", () => {
    render(<SystemCard {...defaultProps} />);
    expect(screen.getByText("Test System")).toBeInTheDocument();
  });

  it("displays the system name", () => {
    render(<SystemCard {...defaultProps} />);
    expect(screen.getByText("Test System")).toBeInTheDocument();
  });

  it("displays the description", () => {
    render(<SystemCard {...defaultProps} />);
    expect(
      screen.getByText("A test system for testing purposes."),
    ).toBeInTheDocument();
  });

  it("renders all features", () => {
    render(<SystemCard {...defaultProps} />);
    expect(screen.getByText("Feature 1")).toBeInTheDocument();
    expect(screen.getByText("Feature 2")).toBeInTheDocument();
    expect(screen.getByText("Feature 3")).toBeInTheDocument();
  });

  it('shows "Active" status for active systems', () => {
    render(<SystemCard {...defaultProps} status="active" />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it('shows "Beta" status for beta systems', () => {
    render(<SystemCard {...defaultProps} status="beta" />);
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it('shows "Coming Soon" status for coming-soon systems', () => {
    render(<SystemCard {...defaultProps} status="coming-soon" />);
    expect(screen.getByText("Coming Soon")).toBeInTheDocument();
  });

  it("renders as a link to the correct href", () => {
    render(<SystemCard {...defaultProps} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/test");
  });

  it("has accessible aria-label", () => {
    render(<SystemCard {...defaultProps} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute(
      "aria-label",
      "Test System system - A test system for testing purposes.",
    );
  });

  it("has a status role for the status badge", () => {
    render(<SystemCard {...defaultProps} />);
    const status = screen.getByRole("status");
    expect(status).toBeInTheDocument();
    expect(status).toHaveAttribute("aria-label", "Status: Active");
  });
});
