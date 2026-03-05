"use client";

import { motion, useReducedMotion } from "framer-motion";

type NumerologyWheelProps = {
  lifePath: number;
  label?: string;
  size?: number;
};

/**
 * Animated circular display for a numerology life path number.
 * A gold ring pulses gently around the central number.
 */
export function NumerologyWheel({
  lifePath,
  label = "Life Path",
  size = 160,
}: NumerologyWheelProps) {
  const prefersReducedMotion = useReducedMotion();

  const radius = size / 2;
  const strokeWidth = 3;
  const innerRadius = radius - strokeWidth * 2;
  const circumference = 2 * Math.PI * innerRadius;

  return (
    <div
      className="flex flex-col items-center gap-3"
      role="img"
      aria-label={`${label}: ${lifePath}`}
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          aria-hidden="true"
        >
          {/* Background ring */}
          <circle
            cx={radius}
            cy={radius}
            r={innerRadius}
            fill="none"
            stroke="rgba(218, 165, 32, 0.12)"
            strokeWidth={strokeWidth}
          />
          {/* Animated gold arc */}
          <motion.circle
            cx={radius}
            cy={radius}
            r={innerRadius}
            fill="none"
            stroke="url(#goldGradient)"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference * 0.25, rotate: -90 }}
            animate={{
              strokeDashoffset: prefersReducedMotion
                ? circumference * 0.25
                : [
                    circumference * 0.25,
                    circumference * 0.15,
                    circumference * 0.25,
                  ],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{ transformOrigin: `${radius}px ${radius}px` }}
          />
          {/* Outer decorative ring */}
          <motion.circle
            cx={radius}
            cy={radius}
            r={radius - 1}
            fill="none"
            stroke="rgba(218, 165, 32, 0.08)"
            strokeWidth={1}
            animate={prefersReducedMotion ? {} : { opacity: [0.4, 0.8, 0.4] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
          <defs>
            <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#b8860b" />
              <stop offset="50%" stopColor="#f0c050" />
              <stop offset="100%" stopColor="#daa520" />
            </linearGradient>
          </defs>
        </svg>

        {/* Center number */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="font-display text-gradient-gold leading-none"
            style={{ fontSize: size * 0.32 }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            {lifePath}
          </motion.span>
        </div>
      </div>

      <p className="text-sm text-text/50 font-body tracking-wider uppercase">
        {label}
      </p>
    </div>
  );
}
