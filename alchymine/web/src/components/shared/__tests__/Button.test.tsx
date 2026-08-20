import { render, screen } from "@testing-library/react";
import Button from "../Button";

describe("Button", () => {
  it("renders its children", () => {
    render(<Button>Start Practice</Button>);
    expect(
      screen.getByRole("button", { name: "Start Practice" }),
    ).toBeInTheDocument();
  });

  it("draws a focus ring that clears the 3:1 contrast floor", () => {
    render(<Button>Start Practice</Button>);
    const button = screen.getByRole("button", { name: "Start Practice" });

    expect(button.className).toContain("focus-visible:ring-2");
    // /60 rather than the /50 this used to carry: /50 computes 2.92:1
    // against the page background, under the 3:1 WCAG 1.4.11 asks of a
    // focus indicator. /60 clears it at 3.74:1 on the background and
    // 3.55:1 on a card surface. Pinned so it cannot drift back down.
    expect(button.className).toContain("focus-visible:ring-primary/60");
  });

  it("keeps the ring on every variant and size", () => {
    const variants = ["primary", "secondary", "ghost"] as const;
    for (const variant of variants) {
      const { unmount } = render(<Button variant={variant}>Go</Button>);
      expect(screen.getByRole("button", { name: "Go" }).className).toContain(
        "focus-visible:ring-primary/60",
      );
      unmount();
    }
  });

  it("announces its loading state and blocks the click", () => {
    render(<Button loading>Save</Button>);
    const button = screen.getByRole("button", { name: /Save/ });

    expect(button).toBeDisabled();
    expect(screen.getByText("Loading")).toBeInTheDocument();
  });
});
