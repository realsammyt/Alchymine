"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Next.js App Router template.tsx — runs on every route change.
 * Provides a subtle cross-fade + upward slide between pages.
 * Respects prefers-reduced-motion: skips the slide, uses a minimal fade.
 */
export default function Template({ children }: { children: ReactNode }) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      initial={{ opacity: 0, y: prefersReducedMotion ? 0 : 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: prefersReducedMotion ? 0 : -10 }}
      transition={{
        duration: prefersReducedMotion ? 0.01 : 0.25,
        ease: [0.22, 1, 0.36, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
