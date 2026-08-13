/**
 * UpsellNotice — component tests.
 *
 * The rail this pins: a quota rejection renders as a wait state with
 * somewhere to go, never as a raw error. That means `role="status"` and
 * not `role="alert"`, the server's own wording, a reset date when there
 * is one, and a working upgrade link.
 */

import { render, screen } from "@testing-library/react";

import UpsellNotice from "@/components/shared/UpsellNotice";
import { PlanGateError } from "@/lib/planGate";

function upgradeRequired(): PlanGateError {
  return new PlanGateError(
    "plan_upgrade_required",
    "Coaching chat is part of a paid plan. Upgrade to start a conversation.",
    null,
    "free",
    "/pricing",
  );
}

function allowanceReached(): PlanGateError {
  return new PlanGateError(
    "plan_allowance_reached",
    "You've used this month's included coaching. Upgrade to keep going.",
    new Date("2026-09-01T00:00:00Z"),
    "pro",
    "/pricing",
  );
}

describe("UpsellNotice", () => {
  it("announces politely rather than as an alert", () => {
    render(<UpsellNotice error={upgradeRequired()} />);

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the server's wording", () => {
    render(<UpsellNotice error={upgradeRequired()} />);

    expect(
      screen.getByText(/Coaching chat is part of a paid plan/),
    ).toBeInTheDocument();
  });

  it("offers a link to the plans", () => {
    render(<UpsellNotice error={upgradeRequired()} />);

    const link = screen.getByRole("link", { name: /see plans/i });
    expect(link).toHaveAttribute("href", "/pricing");
  });

  it("says when the allowance comes back", () => {
    render(<UpsellNotice error={allowanceReached()} />);

    expect(screen.getByText(/Resets on September 1/)).toBeInTheDocument();
  });

  it("says nothing about a reset when waiting would not help", () => {
    render(<UpsellNotice error={upgradeRequired()} />);

    expect(screen.queryByText(/Resets on/)).not.toBeInTheDocument();
  });

  it("keeps the upgrade link reachable by keyboard", () => {
    render(<UpsellNotice error={allowanceReached()} />);

    const link = screen.getByRole("link", { name: /see plans/i });
    link.focus();
    expect(link).toHaveFocus();
  });

  it("does not steal focus when it appears", () => {
    // The banner answers something the user just did and the live region
    // announces it. Moving focus would drop them out of the control they
    // were using.
    const { container } = render(<UpsellNotice error={allowanceReached()} />);

    expect(document.activeElement).toBe(document.body);
    expect(container.querySelector("[autofocus]")).toBeNull();
  });

  it("follows the house copy rules", () => {
    const banned = [
      "delve",
      "leverage",
      "robust",
      "comprehensive",
      "seamless",
      "ensure",
      "foster",
      "utilize",
    ];

    render(<UpsellNotice error={allowanceReached()} />);
    const text = screen.getByRole("status").textContent ?? "";

    expect(text).not.toContain("—");
    for (const word of banned) {
      expect(text.toLowerCase()).not.toContain(word);
    }
  });
});
