"use client";

import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { MotionReveal } from "@/components/shared/MotionReveal";
import { resetPassword, friendlyAuthError } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (!token) {
      setError("Missing reset token. Please use the link from your email.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(friendlyAuthError(err, "reset-password"));
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="w-full max-w-md">
        <MotionReveal>
          <div className="card-surface p-6 text-center space-y-4">
            <div className="w-12 h-12 mx-auto rounded-full bg-accent/20 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-accent"
                aria-hidden="true"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <h2 className="font-display text-xl font-light text-text">
              Password Reset
            </h2>
            <p className="text-text/50 text-sm font-body">
              Your password has been updated successfully.
            </p>
            <Link
              href="/login"
              className="inline-block text-sm font-body text-primary hover:text-primary/80 transition-colors"
            >
              Sign in with your new password
            </Link>
          </div>
        </MotionReveal>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="w-full max-w-md">
        <MotionReveal>
          <div className="card-surface p-6 text-center space-y-4">
            <h2 className="font-display text-xl font-light text-text">
              Invalid Reset Link
            </h2>
            <p className="text-text/50 text-sm font-body">
              This password reset link is invalid or has expired. Please request
              a new one.
            </p>
            <Link
              href="/forgot-password"
              className="inline-block text-sm font-body text-primary hover:text-primary/80 transition-colors"
            >
              Request new reset link
            </Link>
          </div>
        </MotionReveal>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <MotionReveal>
        <div className="text-center mb-8">
          <Link
            href="/"
            className="inline-block font-display text-2xl font-light tracking-wide text-gradient-gold mb-6 hover:opacity-80 transition-opacity"
            aria-label="Alchymine home"
          >
            Alchymine
          </Link>
          <h1 className="font-display text-display-md font-light text-gradient-gold">
            New Password
          </h1>
          <hr className="rule-gold my-6 max-w-[120px] mx-auto" />
          <p className="text-text/50 mt-2 font-body">
            Enter your new password below
          </p>
        </div>
      </MotionReveal>

      <MotionReveal delay={0.1}>
        <form onSubmit={handleSubmit} className="card-surface p-6 space-y-5">
          {error && (
            <div
              role="alert"
              aria-live="assertive"
              className="bg-primary-dark/10 border border-primary-dark/20 text-primary-dark text-sm font-body rounded-xl p-3"
            >
              {error}
            </div>
          )}

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-body font-medium text-text/60 mb-2"
            >
              New Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all duration-300 [color-scheme:dark]"
              placeholder="Min 8 characters"
            />
          </div>

          <div>
            <label
              htmlFor="confirm-password"
              className="block text-sm font-body font-medium text-text/60 mb-2"
            >
              Confirm New Password
            </label>
            <input
              id="confirm-password"
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all duration-300 [color-scheme:dark]"
              placeholder="Re-enter new password"
            />
          </div>

          <Button type="submit" loading={loading} className="w-full">
            Reset Password
          </Button>

          <p className="text-center text-sm font-body text-text/40">
            Remember your password?{" "}
            <Link
              href="/login"
              className="text-primary hover:text-primary/80 transition-colors"
            >
              Sign in
            </Link>
          </p>
        </form>
      </MotionReveal>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="grain-overlay min-h-screen flex items-center justify-center px-4 py-8">
      <div className="bg-atmosphere min-h-screen absolute inset-0" />
      <div className="relative z-10">
        <Suspense>
          <ResetPasswordForm />
        </Suspense>
      </div>
    </main>
  );
}
