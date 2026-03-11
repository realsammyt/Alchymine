"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { useAuth } from "@/lib/AuthContext";
import { friendlyAuthError, joinWaitlist } from "@/lib/api";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function SignupPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [promoCode, setPromoCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Waitlist
  const [waitlistEmail, setWaitlistEmail] = useState("");
  const [waitlistLoading, setWaitlistLoading] = useState(false);
  const [waitlistSuccess, setWaitlistSuccess] = useState(false);
  const [waitlistError, setWaitlistError] = useState("");

  async function handleWaitlist(e: FormEvent) {
    e.preventDefault();
    setWaitlistError("");
    setWaitlistLoading(true);
    try {
      await joinWaitlist(waitlistEmail);
      setWaitlistSuccess(true);
    } catch {
      setWaitlistError("Something went wrong. Please try again.");
    } finally {
      setWaitlistLoading(false);
    }
  }

  useEffect(() => {
    const invite = searchParams.get("invite");
    if (invite) setPromoCode(invite);
  }, [searchParams]);

  function validate(): string | null {
    if (password.length < 8) return "Password must be at least 8 characters";
    if (password !== confirmPassword) return "Passwords do not match";
    if (!promoCode.trim()) return "Invitation code is required";
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      await register(email, password, promoCode.trim());
      router.push("/dashboard");
    } catch (err) {
      setError(friendlyAuthError(err, "signup"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grain-overlay min-h-screen flex items-center justify-center px-4 py-8 sm:py-4">
      <div className="bg-atmosphere w-full max-w-md">
        <div className="text-center mb-8">
          <Link
            href="/"
            className="inline-block font-display text-2xl font-light tracking-wide text-gradient-gold mb-6 hover:opacity-80 transition-opacity"
            aria-label="Alchymine home"
          >
            Alchymine
          </Link>
          <h1 className="font-display text-display-md font-light text-gradient-gold">
            Create Account
          </h1>
          <hr className="rule-gold my-6 max-w-[120px] mx-auto" />
          <p className="text-text/50 mt-2 font-body">
            Join Alchymine to begin your transformation
          </p>
        </div>

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
                className="block font-body text-sm font-medium text-text/70 mb-1.5"
              >
                Email{" "}
                <span className="text-primary/60" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="email"
                type="email"
                required
                aria-required="true"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block font-body text-sm font-medium text-text/70 mb-1.5"
              >
                Password{" "}
                <span className="text-primary/60" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="password"
                type="password"
                required
                aria-required="true"
                autoComplete="new-password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                placeholder="Min 8 characters"
              />
            </div>

            <div>
              <label
                htmlFor="confirm-password"
                className="block font-body text-sm font-medium text-text/70 mb-1.5"
              >
                Confirm Password{" "}
                <span className="text-primary/60" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="confirm-password"
                type="password"
                required
                aria-required="true"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                placeholder="Re-enter password"
              />
            </div>

            <div>
              <label
                htmlFor="promo-code"
                className="block font-body text-sm font-medium text-text/70 mb-1.5"
              >
                Invitation Code{" "}
                <span className="text-primary/60" aria-hidden="true">
                  *
                </span>
              </label>
              <input
                id="promo-code"
                type="text"
                required
                aria-required="true"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                placeholder="Enter your invitation code"
              />
            </div>

            <Button type="submit" loading={loading} className="w-full">
              Create Account
            </Button>

            <p className="text-center text-sm text-text/40">
              Already have an account?{" "}
              <Link
                href="/login"
                className="text-primary hover:text-primary/80 transition-colors"
              >
                Sign in
              </Link>
            </p>
          </form>
        </MotionReveal>

        {/* ── Waitlist module ──────────────────────────────────────── */}
        <MotionReveal delay={0.2}>
          <div className="mt-6 card-surface p-6">
            <div className="flex items-center gap-3 mb-4">
              <hr className="flex-1 border-white/[0.06]" />
              <span className="text-xs font-body text-text/30 whitespace-nowrap">
                Don&apos;t have an invitation code?
              </span>
              <hr className="flex-1 border-white/[0.06]" />
            </div>

            {waitlistSuccess ? (
              <div className="text-center py-2">
                <p className="text-sm font-body text-primary">
                  You&apos;re on the list — we&apos;ll be in touch!
                </p>
              </div>
            ) : (
              <form onSubmit={handleWaitlist} className="space-y-3">
                {waitlistError && (
                  <div
                    role="alert"
                    className="bg-primary-dark/10 border border-primary-dark/20 text-primary-dark text-sm font-body rounded-xl p-3"
                  >
                    {waitlistError}
                  </div>
                )}
                <div>
                  <label
                    htmlFor="waitlist-email"
                    className="block font-body text-sm font-medium text-text/70 mb-1.5"
                  >
                    Join the Waitlist
                  </label>
                  <input
                    id="waitlist-email"
                    type="email"
                    required
                    value={waitlistEmail}
                    onChange={(e) => setWaitlistEmail(e.target.value)}
                    className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                    placeholder="you@example.com"
                  />
                </div>
                <Button
                  type="submit"
                  loading={waitlistLoading}
                  className="w-full"
                >
                  Join Waitlist
                </Button>
              </form>
            )}
          </div>
        </MotionReveal>
      </div>
    </main>
  );
}
