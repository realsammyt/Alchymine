"use client";

interface ProgressBarProps {
  /** Progress value from 0 to 100 */
  value: number;
  /** Optional label shown above the bar */
  label?: string;
  /** Show percentage text */
  showPercentage?: boolean;
  /** Color variant */
  variant?: "gold" | "purple" | "teal";
  /** Height of the bar */
  size?: "sm" | "md" | "lg";
  /** Whether to animate the shimmer */
  animated?: boolean;
}

const variantStyles: Record<string, string> = {
  gold: "bg-gradient-to-r from-primary-dark to-primary",
  purple: "bg-gradient-to-r from-secondary-dark to-secondary",
  teal: "bg-gradient-to-r from-accent-dark to-accent",
};

const sizeStyles: Record<string, string> = {
  sm: "h-1.5",
  md: "h-2.5",
  lg: "h-4",
};

export default function ProgressBar({
  value,
  label,
  showPercentage = false,
  variant = "gold",
  size = "md",
  animated = true,
}: ProgressBarProps) {
  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && <span className="text-sm text-text/60">{label}</span>}
          {showPercentage && (
            <span className="text-sm font-medium text-primary">
              {Math.round(clampedValue)}%
            </span>
          )}
        </div>
      )}
      <div
        className={`w-full bg-surface rounded-full overflow-hidden ${sizeStyles[size]}`}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${variantStyles[variant]} ${animated ? "relative overflow-hidden" : ""}`}
          style={{ width: `${clampedValue}%` }}
        >
          {animated && (
            <div className="absolute inset-0 shimmer-gold opacity-50" />
          )}
        </div>
      </div>
    </div>
  );
}
