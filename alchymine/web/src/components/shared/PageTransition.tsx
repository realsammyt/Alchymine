"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Framer-motion page transition wrapper.
 * Extracted from template.tsx so it can be dynamically imported,
 * keeping framer-motion (~40KB gzipped) out of the initial bundle.
 */
export default function PageTransition({
  children,
}: {
  children: ReactNode;
}) {
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
