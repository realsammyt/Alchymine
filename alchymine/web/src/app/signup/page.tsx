"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { useAuth } from "@/lib/AuthContext";
import { ApiError } from "@/lib/api";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function SignupPage() {
  const router = useRouter();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [promoCode, setPromoCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grain-overlay min-h-screen flex items-center justify-center px-4">
      <div className="bg-atmosphere w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-display-md font-light text-gradient-gold">
            Create Account
          </h1>
          <hr className="rule-gold my-6 max-w-[120px] mx-auto" />
          <p className="text-text/50 mt-2">
            Join Alchymine to begin your transformation
          </p>
        </div>

        <MotionReveal delay={0.1}>
          <form onSubmit={handleSubmit} className="card-surface p-6 space-y-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3">
                {error}
              </div>
            )}

            <div>
              <label
                htmlFor="email"
                className="block font-body text-sm font-medium text-text/70 mb-1.5"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                required
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
                Password
              </label>
              <input
                id="password"
                type="password"
                required
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
                Confirm Password
              </label>
              <input
                id="confirm-password"
                type="password"
                required
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
                Invitation Code
              </label>
              <input
                id="promo-code"
                type="text"
                required
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
      </div>
    </main>
  );
}
