import { render, screen } from "@testing-library/react";

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

// Mock useAuth — return demo account so demo data is visible in tests
jest.mock("@/lib/AuthContext", () => ({
  useAuth: () => ({
    user: { email: "tyler.sammy+demo@gmail.com" },
    isLoading: false,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  }),
}));

// Mock the useApi and getStoredIntake
jest.mock("@/lib/useApi", () => ({
  useApi: () => ({
    data: null,
    loading: false,
    error: null,
    refetch: jest.fn(),
  }),
  getStoredIntake: () => null,
}));

// Mock the API functions
jest.mock("@/lib/api", () => ({
  getWealthProfile: jest.fn(),
  getWealthLevers: jest.fn(),
}));

import WealthPage from "@/app/wealth/page";

describe("Wealth Page Charts", () => {
  it("renders without crashing", () => {
    render(<WealthPage />);
    expect(screen.getByText("Generational Wealth")).toBeInTheDocument();
  });

  it("renders the debt payoff timeline section", () => {
    render(<WealthPage />);
    expect(screen.getByTestId("debt-payoff-timeline")).toBeInTheDocument();
    expect(screen.getByText("Debt Payoff Timeline")).toBeInTheDocument();
  });

  it("displays all demo debts in the timeline", () => {
    render(<WealthPage />);
    const timeline = screen.getByTestId("debt-payoff-timeline");
    expect(timeline).toHaveTextContent("Student Loans");
    expect(timeline).toHaveTextContent("Credit Card");
    expect(timeline).toHaveTextContent("Car Loan");
    expect(timeline).toHaveTextContent("Personal Loan");
  });

  it("shows APR rates for debts", () => {
    render(<WealthPage />);
    expect(screen.getByText("5.5% APR")).toBeInTheDocument();
    expect(screen.getByText("19.9% APR")).toBeInTheDocument();
    expect(screen.getByText("4.2% APR")).toBeInTheDocument();
    expect(screen.getByText("7.8% APR")).toBeInTheDocument();
  });

  it("renders the budget breakdown section", () => {
    render(<WealthPage />);
    expect(screen.getByTestId("budget-breakdown")).toBeInTheDocument();
    expect(screen.getByText("Budget Breakdown")).toBeInTheDocument();
  });

  it("displays budget categories", () => {
    render(<WealthPage />);
    expect(screen.getByText("Housing")).toBeInTheDocument();
    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(screen.getByText("Savings")).toBeInTheDocument();
  });

  it("shows the savings rate", () => {
    render(<WealthPage />);
    expect(screen.getByText("Savings Rate")).toBeInTheDocument();
    // Savings: 700 / 5800 = ~12%
    expect(screen.getByText("12%")).toBeInTheDocument();
  });

  it("renders the net worth tracker section", () => {
    render(<WealthPage />);
    expect(screen.getByTestId("net-worth-tracker")).toBeInTheDocument();
    expect(screen.getByText("Net Worth Summary")).toBeInTheDocument();
  });

  it("displays assets and liabilities", () => {
    render(<WealthPage />);
    expect(screen.getByText("Savings Account")).toBeInTheDocument();
    expect(screen.getByText("Investment Portfolio")).toBeInTheDocument();
    expect(screen.getByText("Retirement (401k)")).toBeInTheDocument();
  });

  it("calculates net worth correctly", () => {
    render(<WealthPage />);
    // Assets: 8500 + 15200 + 22300 + 12000 = 58000
    // Liabilities: 12400 + 2800 + 8200 + 1200 = 24600
    // Net Worth: 58000 - 24600 = 33400
    expect(screen.getByText("$33,400")).toBeInTheDocument();
  });

  it("shows the avalanche method label", () => {
    render(<WealthPage />);
    expect(
      screen.getByText("Avalanche Method (highest rate first)"),
    ).toBeInTheDocument();
  });

  it("renders the financial dashboard section", () => {
    render(<WealthPage />);
    expect(screen.getByText("Financial Dashboard")).toBeInTheDocument();
  });

  it("displays the not-financial-advice disclaimer", () => {
    render(<WealthPage />);
    expect(
      screen.getByText(
        "Not financial advice. All strategies require professional review.",
      ),
    ).toBeInTheDocument();
  });
});
