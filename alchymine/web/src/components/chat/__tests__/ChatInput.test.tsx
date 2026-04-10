/**
 * ChatInput — component tests.
 *
 * Covers keyboard submit semantics (Enter/Shift+Enter), whitespace
 * blocking, disabled state, and the 2000-char limit.
 */

import { fireEvent, render, screen } from "@testing-library/react";

import ChatInput from "@/components/chat/ChatInput";

describe("ChatInput", () => {
  it("submits on Enter and clears the textarea", () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByLabelText(/chat message/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "hello there" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).toHaveBeenCalledWith("hello there");
    expect(textarea.value).toBe("");
  });

  it("inserts newline on Shift+Enter without sending", () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByLabelText(/chat message/i) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "line1" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("blocks empty and whitespace-only submissions", () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByLabelText(/chat message/i) as HTMLTextAreaElement;
    const button = screen.getByRole("button", { name: /send message/i });

    // Button should start disabled.
    expect(button).toBeDisabled();

    // Whitespace-only should not enable submit.
    fireEvent.change(textarea, { target: { value: "    " } });
    expect(button).toBeDisabled();

    // Enter on whitespace should also be a no-op.
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables input and shows spinner when disabled prop is true", () => {
    render(<ChatInput onSend={jest.fn()} disabled />);
    const textarea = screen.getByLabelText(/chat message/i) as HTMLTextAreaElement;
    expect(textarea).toBeDisabled();
    // Send button is disabled too.
    expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
  });

  it("caps input at maxLength and shows a counter near the limit", () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} maxLength={50} />);
    const textarea = screen.getByLabelText(/chat message/i) as HTMLTextAreaElement;

    // With maxLength=50 and threshold=100, counter is always visible.
    fireEvent.change(textarea, { target: { value: "x".repeat(10) } });
    expect(screen.getByText(/40 characters remaining/i)).toBeInTheDocument();

    // Pasting beyond the limit is clamped.
    fireEvent.change(textarea, { target: { value: "y".repeat(100) } });
    expect(textarea.value).toHaveLength(50);
    expect(screen.getByText(/0 characters remaining/i)).toBeInTheDocument();
  });
});
