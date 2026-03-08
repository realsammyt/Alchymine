"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";

/**
 * Next.js App Router template.tsx — runs on every route change.
 *
 * The actual framer-motion page transition is dynamically imported so
 * the ~40KB (gzipped) framer-motion bundle is code-split and loaded
 * lazily on the client, keeping the initial JS payload smaller.
 */
const PageTransition = dynamic(
  () => import("@/components/shared/PageTransition"),
  { ssr: false },
);

export default function Template({ children }: { children: ReactNode }) {
  return <PageTransition>{children}</PageTransition>;
}
