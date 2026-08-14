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
    // A fieldset with a legend is already a named group. No explicit
    // role=radiogroup, which only duplicated what the markup said.
    renderPrompt();

    expect(
      screen.getByRole("group", { name: /how much of that capacity/i }),
    ).toBeInTheDocument();
    // Five readings plus the way back to no answer.
    expect(screen.getAllByRole("radio")).toHaveLength(6);
  });

  it("starts with nothing selected", () => {
    // "Rather not say" submits null and so does an untouched group, but
    // they are different states on screen. Keying the option off null
    // drew it pre-selected before the user had answered anything.
    renderPrompt();

    for (const radio of screen.getAllByRole("radio")) {
      expect(radio).not.toBeChecked();
    }
  });

  it("lets the user return to no answer after choosing one", () => {
    // The copy calls this optional, and a radio group cannot otherwise
    // be cleared once anything is picked.
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("radio", { name: /a bit more/i }));
    fireEvent.click(screen.getByRole("radio", { name: /rather not say/i }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(props.onSubmit).toHaveBeenCalledWith({
      capacityDelta: null,
      note: "",
    });
  });

  it("lets the user dismiss it entirely", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("button", { name: /not now/i }));

    expect(props.onDismiss).toHaveBeenCalledTimes(1);
    expect(props.onSubmit).not.toHaveBeenCalled();
  });

  it("blocks saving while a write is in flight without blurring the control", () => {
    renderPrompt({ state: "saving" });

    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toHaveAttribute("aria-disabled", "true");
    expect(save).toHaveAttribute("aria-busy", "true");
    expect(save).not.toBeDisabled();
    save.focus();
    expect(save).toHaveFocus();
  });

  it("does not submit again while a write is in flight", () => {
    const { props } = renderPrompt({ state: "saving" });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(props.onSubmit).not.toHaveBeenCalled();
  });

  it("keeps a stable accessible name while saving", () => {
    renderPrompt({ state: "saving" });
    expect(screen.queryByRole("button", { name: /saving/i })).toBeNull();
  });

  it("confirms once saved, in a status region that takes focus", () => {
    const { rerender, props } = renderPrompt();
    rerender(<IntegrationPrompt {...props} state="saved" />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(/logged/i);
    expect(status).toHaveFocus();
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
