import { fireEvent, render, screen } from "@testing-library/react";
import IntegrationPrompt from "../IntegrationPrompt";

function renderPrompt(
  overrides: Partial<React.ComponentProps<typeof IntegrationPrompt>> = {},
) {
  const props = {
    practiceTitle: "Find the Floor",
    onSubmit: jest.fn().mockResolvedValue(undefined),
    onDismiss: jest.fn(),
    state: "idle" as const,
    error: null,
    ...overrides,
  };
  return { ...render(<IntegrationPrompt {...props} />), props };
}

describe("IntegrationPrompt", () => {
  it("names the practice it is following up on", () => {
    renderPrompt();
    expect(screen.getByText(/Find the Floor/)).toBeInTheDocument();
  });

  it("offers the journal template as a link, not a form field", () => {
    renderPrompt();

    const link = screen.getByRole("link", { name: /journal/i });
    expect(link).toHaveAttribute("href", "/journal?template=practice-integration");
  });

  it("submits with no capacity reading when none is chosen", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(props.onSubmit).toHaveBeenCalledWith({
      capacityDelta: null,
      note: "",
    });
  });

  it("submits the chosen capacity reading and note", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("radio", { name: /a bit more/i }));
    fireEvent.change(screen.getByLabelText(/anything else/i), { target: { value: "Surprised me." } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(props.onSubmit).toHaveBeenCalledWith({
      capacityDelta: 1,
      note: "Surprised me.",
    });
  });

  it("groups the capacity choices under one accessible name", () => {
    renderPrompt();
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    expect(screen.getAllByRole("radio")).toHaveLength(5);
  });

  it("lets the user dismiss it entirely", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("button", { name: /not now/i }));

    expect(props.onDismiss).toHaveBeenCalledTimes(1);
    expect(props.onSubmit).not.toHaveBeenCalled();
  });

  it("disables the save control while saving", () => {
    renderPrompt({ state: "saving" });
    expect(screen.getByRole("button", { name: /sav/i })).toBeDisabled();
  });

  it("confirms once saved", () => {
    renderPrompt({ state: "saved" });
    expect(screen.getByText(/logged/i)).toBeInTheDocument();
  });

  it("shows an error and keeps the save control usable", () => {
    renderPrompt({ state: "error", error: "That didn't save. Try again." });

    expect(screen.getByText("That didn't save. Try again.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toBeEnabled();
  });

  it("reaches the radios and the save control by keyboard", () => {
    const { props } = renderPrompt();

    // Real radio inputs, so arrow-key navigation inside the group is the
    // browser's job rather than something this component reimplements.
    for (const radio of screen.getAllByRole("radio")) {
      expect(radio.tagName).toBe("INPUT");
      expect(radio).toHaveAttribute("type", "radio");
      radio.focus();
      expect(radio).toHaveFocus();
    }

    for (const control of screen.getAllByRole("button")) {
      expect(control).not.toHaveAttribute("tabindex", "-1");
      expect(control.className).toMatch(/focus-visible:/);
    }

    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(props.onSubmit).toHaveBeenCalled();
  });
});
