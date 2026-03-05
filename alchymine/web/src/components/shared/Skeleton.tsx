"use client";

interface SkeletonCardProps {
  className?: string;
}

interface SkeletonTextProps {
  width?: "full" | "3/4" | "1/2" | "1/4";
  className?: string;
}

interface SkeletonCircleProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

/**
 * Card-shaped skeleton placeholder for loading states.
 * Replaces a full content card while data is being fetched.
 */
export function SkeletonCard({ className = "" }: SkeletonCardProps) {
  return (
    <div
      className={`animate-pulse bg-white/[0.06] rounded-2xl p-6 space-y-4 ${className}`}
      aria-hidden="true"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-white/[0.08] flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-white/[0.08] rounded-lg w-3/4" />
          <div className="h-3 bg-white/[0.05] rounded-lg w-1/2" />
        </div>
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-white/[0.06] rounded-lg w-full" />
        <div className="h-3 bg-white/[0.06] rounded-lg w-5/6" />
        <div className="h-3 bg-white/[0.06] rounded-lg w-4/6" />
      </div>
    </div>
  );
}

/**
 * Text line skeleton placeholder for loading states.
 * Use configurable width to simulate different line lengths.
 */
export function SkeletonText({
  width = "full",
  className = "",
}: SkeletonTextProps) {
  const widthClass = {
    full: "w-full",
    "3/4": "w-3/4",
    "1/2": "w-1/2",
    "1/4": "w-1/4",
  }[width];

  return (
    <div
      className={`animate-pulse h-4 bg-white/[0.06] rounded-lg ${widthClass} ${className}`}
      aria-hidden="true"
    />
  );
}

/**
 * Circular skeleton placeholder for avatars, icons, or ring charts.
 */
export function SkeletonCircle({
  size = "md",
  className = "",
}: SkeletonCircleProps) {
  const sizeClass = {
    sm: "w-8 h-8",
    md: "w-12 h-12",
    lg: "w-20 h-20",
  }[size];

  return (
    <div
      className={`animate-pulse bg-white/[0.06] rounded-full ${sizeClass} ${className}`}
      aria-hidden="true"
    />
  );
}
