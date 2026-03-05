"use client";

import { SkeletonCard, SkeletonText } from "@/components/shared/Skeleton";

interface PillarPageSkeletonProps {
  sections?: number;
}

/**
 * Generic skeleton screen for any pillar page.
 * Shows while pillar content is loading.
 */
export function PillarPageSkeleton({ sections = 3 }: PillarPageSkeletonProps) {
  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-10 sm:py-12"
      aria-busy="true"
      aria-label="Loading content"
    >
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Page header skeleton */}
        <div className="space-y-3">
          <div className="h-3 bg-white/[0.06] rounded-lg w-24 animate-pulse" />
          <div className="h-9 bg-white/[0.06] rounded-lg w-64 animate-pulse" />
          <div className="h-4 bg-white/[0.05] rounded-lg w-80 animate-pulse" />

          {/* Methodology button skeleton */}
          <div className="flex gap-3 mt-4">
            <div className="h-9 w-40 bg-white/[0.06] rounded-xl animate-pulse" />
            <div className="h-9 w-28 bg-white/[0.04] rounded-xl animate-pulse" />
          </div>

          <div className="h-px bg-white/[0.06] w-20 mt-4" />
        </div>

        {/* Content sections */}
        {Array.from({ length: sections }).map((_, i) => (
          <div key={i} className="card-surface p-6 space-y-4">
            {/* Section header */}
            <div className="flex items-center justify-between">
              <div className="h-5 bg-white/[0.06] rounded-lg w-40 animate-pulse" />
              <div className="h-6 w-20 bg-white/[0.04] rounded-full animate-pulse" />
            </div>

            <div className="h-px bg-white/[0.04]" />

            {/* Content varies by section index for visual interest */}
            {i === 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : i === 1 ? (
              <div className="space-y-3">
                <SkeletonText width="full" />
                <SkeletonText width="3/4" />
                <SkeletonText width="full" />
                <SkeletonText width="1/2" />
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {Array.from({ length: 3 }).map((_, j) => (
                  <div
                    key={j}
                    className="bg-white/[0.04] rounded-xl p-4 space-y-2"
                  >
                    <div className="h-4 bg-white/[0.06] rounded-lg w-3/4 animate-pulse" />
                    <div className="h-3 bg-white/[0.04] rounded-lg w-full animate-pulse" />
                    <div className="h-3 bg-white/[0.04] rounded-lg w-5/6 animate-pulse" />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default PillarPageSkeleton;
