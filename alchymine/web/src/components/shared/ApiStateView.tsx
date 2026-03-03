"use client";

import Button from "./Button";

interface ApiStateViewProps {
  loading: boolean;
  error: string | null;
  empty?: boolean;
  loadingText?: string;
  emptyText?: string;
  emptyIcon?: string;
  onRetry?: () => void;
  children: React.ReactNode;
}

/**
 * Handles loading, error, and empty states for API-driven sections.
 * Renders children only when data is ready.
 */
export default function ApiStateView({
  loading,
  error,
  empty = false,
  loadingText = "Loading...",
  emptyText = "No data available yet. Complete your profile to see personalized results.",
  emptyIcon = "\u{1F4CB}",
  onRetry,
  children,
}: ApiStateViewProps) {
  if (loading) {
    return (
      <div
        className="card-surface p-8 text-center"
        role="status"
        aria-live="polite"
      >
        <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto mb-3" />
        <p className="text-text/50 text-sm">{loadingText}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-surface p-6 border-l-2 border-primary-dark/30">
        <div className="flex items-start gap-3">
          <span
            className="text-primary-dark text-lg flex-shrink-0"
            aria-hidden="true"
          >
            {"\u26A0\uFE0F"}
          </span>
          <div className="flex-1">
            <p className="text-sm font-medium text-text/80 mb-1">
              Could not load data
            </p>
            <p className="text-xs text-text/40 mb-3">{error}</p>
            {onRetry && (
              <Button variant="ghost" size="sm" onClick={onRetry}>
                Try Again
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (empty) {
    return (
      <div className="card-surface p-8 text-center">
        <div className="text-3xl mb-3" aria-hidden="true">
          {emptyIcon}
        </div>
        <p className="text-text/50 text-sm max-w-md mx-auto">{emptyText}</p>
        <a
          href="/discover/intake"
          className="inline-block mt-4 text-primary text-sm font-medium hover:underline"
        >
          Start Your Profile
        </a>
      </div>
    );
  }

  return <>{children}</>;
}
