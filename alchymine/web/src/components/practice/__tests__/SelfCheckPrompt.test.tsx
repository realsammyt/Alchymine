import { fireEvent, render, screen } from "@testing-library/react";
import SelfCheckPrompt from "../SelfCheckPrompt";

const QUESTION = "Were you settling, or were you trying to make something go away?";

function renderPrompt(
  overrides: Partial<React.ComponentProps<typeof SelfCheckPrompt>> = {},
) {
  const props = {
    question: QUESTION,
    onSave: jest.fn().mockResolvedValue(undefined),
    onDismiss: jest.fn(),
    saving: false,
    saved: false,
    error: null,
    ...overrides,
  };
  return { ...render(<SelfCheckPrompt {...props} />), props };
}

describe("SelfCheckPrompt", () => {
  it("asks the reflective question", () => {
    renderPrompt();
    expect(screen.getByText(QUESTION)).toBeInTheDocument();
  });

  it("labels the box as optional and says nothing is scored", () => {
    renderPrompt();

    expect(screen.getByText(/optional/i)).toBeInTheDocument();
    expect(
      screen.getByText(/nobody scores this|not scored|no right answer/i),
    ).toBeInTheDocument();
  });

  it("gives the free-text box an accessible label", () => {
    renderPrompt();
    expect(screen.getByLabelText(QUESTION)).toBeInTheDocument();
  });

  it("passes the typed response to onSave", async () => {
    const { props } = renderPrompt();

    fireEvent.change(screen.getByLabelText(QUESTION), { target: { value: "Settling, mostly." } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(props.onSave).toHaveBeenCalledWith("Settling, mostly.");
  });

  it("lets the user leave without answering", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("button", { name: /skip/i }));

    expect(props.onDismiss).toHaveBeenCalledTimes(1);
    expect(props.onSave).not.toHaveBeenCalled();
  });

  it("does not save an empty response", async () => {
    const { props } = renderPrompt();

    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(props.onSave).not.toHaveBeenCalled();
  });

  it("reaches the box and both controls by keyboard", () => {
    const { props } = renderPrompt();

    const box = screen.getByLabelText(QUESTION);
    expect(box.tagName).toBe("TEXTAREA");
    box.focus();
    expect(box).toHaveFocus();

    // Save only becomes reachable once there is something to save,
    // which is the point: an enabled control that does nothing is worse
    // than a disabled one that says why.
    fireEvent.change(box, { target: { value: "Something true." } });

    for (const control of screen.getAllByRole("button")) {
      expect(control.tagName).toBe("BUTTON");
      expect(control).not.toHaveAttribute("tabindex", "-1");
      control.focus();
      expect(control).toHaveFocus();
      expect(control.className).toMatch(/focus-visible:/);
    }

    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(props.onSave).toHaveBeenCalledWith("Something true.");
  });

  it("blocks saving while a write is in flight without blurring the control", () => {
    // aria-disabled, not disabled: the real attribute drops the button
    // out of the tab order and blurs whoever is standing on it.
    renderPrompt({ saving: true });

    const save = screen.getByRole("button", { name: "Save this" });
    expect(save).toHaveAttribute("aria-disabled", "true");
    expect(save).toHaveAttribute("aria-busy", "true");
    expect(save).not.toBeDisabled();
    save.focus();
    expect(save).toHaveFocus();
  });

  it("keeps a stable accessible name while saving", () => {
    renderPrompt({ saving: true });
    expect(screen.queryByRole("button", { name: /saving/i })).toBeNull();
  });

  it("keeps the save control reachable before anything is typed", () => {
    // Disabled would hide the affordance: a keyboard user would tab from
    // the textarea straight to "Skip this" and never learn Save exists.
    renderPrompt();

    const save = screen.getByRole("button", { name: "Save this" });
    expect(save).not.toBeDisabled();
    expect(save).toHaveAttribute("aria-disabled", "true");
  });

  it("confirms the save in a status region and takes focus", () => {
    const { rerender, props } = renderPrompt();
    rerender(<SelfCheckPrompt {...props} saved />);

    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("Saved. Only you see this.");
    expect(status).toHaveFocus();
  });

  it("surfaces a save error without losing what was typed", async () => {
    renderPrompt({ error: "That didn't save. Try again." });

    fireEvent.change(screen.getByLabelText(QUESTION), { target: { value: "Kept text" } });

    expect(screen.getByText("That didn't save. Try again.")).toBeInTheDocument();
    expect(screen.getByLabelText(QUESTION)).toHaveValue("Kept text");
  });
});
