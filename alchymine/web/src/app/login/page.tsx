"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { useAuth } from "@/lib/AuthContext";
import { ApiError } from "@/lib/api";
import { MotionReveal } from "@/components/shared/MotionReveal";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
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
            Welcome Back
          </h1>
          <hr className="rule-gold my-6 max-w-[120px] mx-auto" />
          <p className="text-text/50 mt-2 font-body">
            Sign in to your Alchymine account
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body placeholder:text-text/25 focus:border-primary/40 focus:ring-1 focus:ring-primary/20 focus:bg-white/[0.05] transition-all duration-300 focus:outline-none text-text"
                placeholder="Your password"
              />
            </div>

            <div className="flex items-center justify-between">
              <Link
                href="/forgot-password"
                className="text-sm text-text/40 hover:text-text/70 transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <Button type="submit" loading={loading} className="w-full">
              Sign In
            </Button>

            <p className="text-center text-sm text-text/40">
              Don&apos;t have an account?{" "}
              <Link
                href="/signup"
                className="text-primary hover:text-primary/80 transition-colors"
              >
                Sign up
              </Link>
            </p>
          </form>
        </MotionReveal>
      </div>
    </main>
  );
}
