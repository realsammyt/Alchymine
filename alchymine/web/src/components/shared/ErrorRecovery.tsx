"use client";

import { useState, useEffect, useRef } from "react";
import Button from "@/components/shared/Button";

// ─── NetworkError ─────────────────────────────────────────────────────

interface NetworkErrorProps {
  onRetry: () => void;
  retryCount?: number;
}

const MAX_AUTO_RETRIES = 3;
const BACKOFF_DELAYS = [2, 4, 8];

export function NetworkError({ onRetry, retryCount = 0 }: NetworkErrorProps) {
  const [countdown, setCountdown] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onRetryRef = useRef(onRetry);
  onRetryRef.current = onRetry;

  const exhausted = retryCount >= MAX_AUTO_RETRIES;

  useEffect(() => {
    if (exhausted) return;

    const delay = BACKOFF_DELAYS[retryCount] ?? 8;
    setCountdown(delay);

    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) return null;
        return prev - 1;
      });
    }, 1000);

    timerRef.current = setTimeout(() => {
      onRetryRef.current();
    }, delay * 1000);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [retryCount, exhausted]);

  function handleManualRetry() {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setCountdown(null);
    onRetry();
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex flex-col items-center gap-4 py-8 px-4 text-center"
    >
      <div
        className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center"
        aria-hidden="true"
      >
        <svg
          className="w-6 h-6 text-red-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M1 1l22 22" />
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
          <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
          <path d="M10.71 5.05A16 16 0 0 1 22.56 9" />
          <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
          <line x1="12" y1="20" x2="12.01" y2="20" />
        </svg>
      </div>

      <div>
        <p className="font-display text-base font-medium text-text">
          Connection lost
        </p>
        {exhausted ? (
          <p className="font-body text-sm text-text/50 mt-1 max-w-xs">
            Still having trouble. Check your connection and try again.
          </p>
        ) : (
          <p className="font-body text-sm text-text/50 mt-1">
            {countdown !== null
              ? `Retrying in ${countdown}s\u2026`
              : "Retrying\u2026"}
          </p>
        )}
      </div>

      <Button variant="ghost" size="sm" onClick={handleManualRetry}>
        Retry now
      </Button>
    </div>
  );
}

// ─── SessionExpired ───────────────────────────────────────────────────

interface SessionExpiredProps {
  onReLogin: (email: string, password: string) => Promise<void>;
}

export function SessionExpired({ onReLogin }: SessionExpiredProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onReLogin(email, password);
    } catch {
      setError("Sign-in failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full bg-white/[0.04] border border-white/[0.10] rounded-xl px-4 py-3 font-body text-sm text-text placeholder:text-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors";

  return (
    <div role="alert" aria-live="polite" className="space-y-4 py-4 px-2">
      <div className="text-center">
        <div
          className="w-10 h-10 rounded-full bg-primary/[0.08] border border-primary/[0.15] flex items-center justify-center mx-auto mb-3"
          aria-hidden="true"
        >
          <svg
            className="w-5 h-5 text-primary/60"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <p className="font-display text-base font-medium text-text">
          Your session has expired
        </p>
        <p className="font-body text-sm text-text/50 mt-1">
          Sign in again to continue.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3" noValidate>
        <div>
          <label
            htmlFor="session-email"
            className="block font-body text-xs text-text/50 mb-1.5"
          >
            Email
          </label>
          <input
            id="session-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="your@email.com"
            className={inputClass}
            autoComplete="email"
            required
          />
        </div>

        <div>
          <label
            htmlFor="session-password"
            className="block font-body text-xs text-text/50 mb-1.5"
          >
            Password
          </label>
          <input
            id="session-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className={inputClass}
            autoComplete="current-password"
            required
          />
        </div>

        {error && (
          <p role="alert" className="font-body text-xs text-red-400">
            {error}
          </p>
        )}

        <Button
          type="submit"
          variant="primary"
          size="sm"
          loading={loading}
          disabled={!email || !password}
          className="w-full"
        >
          Sign in
        </Button>
      </form>
    </div>
  );
}

// ─── GenerationFailed ─────────────────────────────────────────────────

interface GenerationFailedProps {
  onRetry: () => void;
  error?: string;
}

export function GenerationFailed({ onRetry, error }: GenerationFailedProps) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex flex-col items-center gap-4 py-8 px-4 text-center"
    >
      <div
        className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center"
        aria-hidden="true"
      >
        <svg
          className="w-6 h-6 text-red-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>

      <div>
        <p className="font-display text-base font-medium text-text">
          Something went wrong generating your report
        </p>
        <p className="font-body text-sm text-text/50 mt-1 max-w-xs">
          {error ?? "This usually resolves on retry."}
        </p>
      </div>

      <Button variant="ghost" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
