"use client";

import { FormEvent, Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Button from "@/components/shared/Button";
import { resetPassword, ApiError } from "@/lib/api";

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
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="w-full max-w-md">
        <div className="card-surface p-6 text-center space-y-4">
          <div className="w-12 h-12 mx-auto rounded-full bg-green-500/20 flex items-center justify-center">
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
              className="text-green-400"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold">Password Reset</h2>
          <p className="text-text/50 text-sm">
            Your password has been updated successfully.
          </p>
          <Link
            href="/login"
            className="inline-block text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Sign in with your new password
          </Link>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="w-full max-w-md">
        <div className="card-surface p-6 text-center space-y-4">
          <h2 className="text-xl font-semibold">Invalid Reset Link</h2>
          <p className="text-text/50 text-sm">
            This password reset link is invalid or has expired. Please request a
            new one.
          </p>
          <Link
            href="/forgot-password"
            className="inline-block text-sm text-primary hover:text-primary/80 transition-colors"
          >
            Request new reset link
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold">
          <span className="text-gradient-gold">New Password</span>
        </h1>
        <p className="text-text/50 mt-2">Enter your new password below</p>
      </div>

      <form onSubmit={handleSubmit} className="card-surface p-6 space-y-5">
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3">
            {error}
          </div>
        )}

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-text/70 mb-1.5"
          >
            New Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-bg border border-white/10 rounded-lg px-4 py-2.5 text-text placeholder-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors"
            placeholder="Min 8 characters"
          />
        </div>

        <div>
          <label
            htmlFor="confirm-password"
            className="block text-sm font-medium text-text/70 mb-1.5"
          >
            Confirm New Password
          </label>
          <input
            id="confirm-password"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full bg-bg border border-white/10 rounded-lg px-4 py-2.5 text-text placeholder-text/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30 transition-colors"
            placeholder="Re-enter new password"
          />
        </div>

        <Button type="submit" loading={loading} className="w-full">
          Reset Password
        </Button>

        <p className="text-center text-sm text-text/40">
          Remember your password?{" "}
          <Link
            href="/login"
            className="text-primary hover:text-primary/80 transition-colors"
          >
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <main className="min-h-screen flex items-center justify-center px-4">
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </main>
  );
}
