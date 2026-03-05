"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { MotionReveal } from "@/components/shared/MotionReveal";
import { forgotPassword, friendlyAuthError } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(friendlyAuthError(err, "forgot-password"));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <main className="grain-overlay min-h-screen flex items-center justify-center px-4 py-8">
        <div className="bg-atmosphere min-h-screen absolute inset-0" />
        <div className="w-full max-w-md relative z-10">
          <MotionReveal>
            <div className="card-surface p-6 text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-full bg-primary/20 flex items-center justify-center">
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
                  className="text-primary"
                  aria-hidden="true"
                >
                  <rect width="20" height="16" x="2" y="4" rx="2" />
                  <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                </svg>
              </div>
              <h2 className="font-display text-xl font-light text-text">
                Check Your Email
              </h2>
              <p className="text-text/50 text-sm font-body">
                If an account exists with{" "}
                <strong className="text-text/70">{email}</strong>, you&apos;ll
                receive password reset instructions shortly.
              </p>
              <Link
                href="/login"
                className="inline-block text-sm font-body text-primary hover:text-primary/80 transition-colors"
              >
                Back to sign in
              </Link>
            </div>
          </MotionReveal>
        </div>
      </main>
    );
  }

  return (
    <main className="grain-overlay min-h-screen flex items-center justify-center px-4 py-8">
      <div className="bg-atmosphere min-h-screen absolute inset-0" />
      <div className="w-full max-w-md relative z-10">
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
              Reset Password
            </h1>
            <hr className="rule-gold my-6 max-w-[120px] mx-auto" />
            <p className="text-text/50 mt-2 font-body">
              Enter your email and we&apos;ll send you reset instructions
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
                htmlFor="email"
                className="block text-sm font-body font-medium text-text/60 mb-2"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition-all duration-300 [color-scheme:dark]"
                placeholder="you@example.com"
              />
            </div>

            <Button type="submit" loading={loading} className="w-full">
              Send Reset Link
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
    </main>
  );
}
