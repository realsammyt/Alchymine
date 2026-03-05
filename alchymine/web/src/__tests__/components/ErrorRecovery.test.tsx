import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  NetworkError,
  SessionExpired,
  GenerationFailed,
} from "@/components/shared/ErrorRecovery";

describe("NetworkError", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders with Connection lost message", () => {
    render(<NetworkError onRetry={jest.fn()} />);
    expect(screen.getByText("Connection lost")).toBeInTheDocument();
  });

  it("renders a Retry now button", () => {
    render(<NetworkError onRetry={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /retry now/i }),
    ).toBeInTheDocument();
  });

  it("calls onRetry when Retry now button is clicked", () => {
    const onRetry = jest.fn();
    render(<NetworkError onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: /retry now/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("shows countdown text when not exhausted", () => {
    render(<NetworkError onRetry={jest.fn()} retryCount={0} />);
    expect(screen.getByText(/Retrying in/)).toBeInTheDocument();
  });

  it("shows exhausted message after 3 retries", () => {
    render(<NetworkError onRetry={jest.fn()} retryCount={3} />);
    expect(screen.getByText(/Still having trouble/)).toBeInTheDocument();
  });

  it("has role=alert for screen reader accessibility", () => {
    render(<NetworkError onRetry={jest.fn()} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("SessionExpired", () => {
  it("renders session expired heading", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByText("Your session has expired")).toBeInTheDocument();
  });

  it("renders sign in again message", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByText("Sign in again to continue.")).toBeInTheDocument();
  });

  it("renders email input", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("your@email.com")).toBeInTheDocument();
  });

  it("renders password input", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("renders a Sign in button", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /sign in/i }),
    ).toBeInTheDocument();
  });

  it("sign in button is disabled when fields are empty", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByRole("button", { name: /sign in/i })).toBeDisabled();
  });

  it("sign in button becomes enabled when fields are filled", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    expect(screen.getByRole("button", { name: /sign in/i })).not.toBeDisabled();
  });

  it("calls onReLogin with email and password when form is submitted", async () => {
    const onReLogin = jest.fn().mockResolvedValue(undefined);
    render(<SessionExpired onReLogin={onReLogin} />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(onReLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("shows error message when onReLogin throws", async () => {
    const onReLogin = jest.fn().mockRejectedValue(new Error("Invalid"));
    render(<SessionExpired onReLogin={onReLogin} />);
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/Sign-in failed/)).toBeInTheDocument();
    });
  });

  it("has role=alert for screen reader accessibility", () => {
    render(<SessionExpired onReLogin={jest.fn()} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("GenerationFailed", () => {
  it("renders generation failed message", () => {
    render(<GenerationFailed onRetry={jest.fn()} />);
    expect(
      screen.getByText("Something went wrong generating your report"),
    ).toBeInTheDocument();
  });

  it("renders default message when no error prop is provided", () => {
    render(<GenerationFailed onRetry={jest.fn()} />);
    expect(
      screen.getByText(/This usually resolves on retry/),
    ).toBeInTheDocument();
  });

  it("renders custom error message when provided", () => {
    render(
      <GenerationFailed onRetry={jest.fn()} error="Report engine timed out." />,
    );
    expect(screen.getByText("Report engine timed out.")).toBeInTheDocument();
  });

  it("renders a retry button", () => {
    render(<GenerationFailed onRetry={jest.fn()} />);
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("calls onRetry when retry button is clicked", () => {
    const onRetry = jest.fn();
    render(<GenerationFailed onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("has role=alert for screen reader accessibility", () => {
    render(<GenerationFailed onRetry={jest.fn()} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
