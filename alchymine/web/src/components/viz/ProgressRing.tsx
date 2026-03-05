"use client";

import { motion, useReducedMotion } from "framer-motion";

type ProgressRingProps = {
  progress: number;
  label: string;
  color?: string;
  size?: number;
  strokeWidth?: number;
};

/**
 * Animated circular progress ring.
 * Animates stroke-dashoffset from empty to the target progress on mount.
 */
export function ProgressRing({
  progress,
  label,
  color = "#daa520",
  size = 120,
  strokeWidth = 6,
}: ProgressRingProps) {
  const prefersReducedMotion = useReducedMotion();

  const clampedProgress = Math.min(100, Math.max(0, progress));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;
  const targetOffset = circumference - (clampedProgress / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center gap-2"
      role="progressbar"
      aria-valuenow={clampedProgress}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`${label}: ${clampedProgress}%`}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          aria-hidden="true"
        >
          {/* Track ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={strokeWidth}
          />
          {/* Progress arc — rotated so 0% starts at top */}
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{
              strokeDashoffset: prefersReducedMotion
                ? targetOffset
                : targetOffset,
            }}
            transition={
              prefersReducedMotion
                ? { duration: 0.01 }
                : { duration: 1, ease: [0.22, 1, 0.36, 1], delay: 0.1 }
            }
            style={{
              transformOrigin: `${center}px ${center}px`,
              rotate: "-90deg",
            }}
          />
        </svg>

        {/* Center percentage */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="font-body font-semibold leading-none"
            style={{ fontSize: size * 0.2, color }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
          >
            {clampedProgress}%
          </motion.span>
        </div>
      </div>

      <p className="text-xs text-text/50 font-body tracking-wide text-center">
        {label}
      </p>
    </div>
  );
}
