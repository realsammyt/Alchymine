"use client";

import {
  SkeletonCard,
  SkeletonText,
  SkeletonCircle,
} from "@/components/shared/Skeleton";

/**
 * Skeleton screen matching the dashboard layout.
 * Shows while dashboard data is loading.
 */
export function DashboardSkeleton() {
  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-10 sm:py-12"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header skeleton */}
        <div className="text-center space-y-3">
          <div className="h-3 bg-white/[0.06] rounded-lg w-32 mx-auto animate-pulse" />
          <div className="h-8 bg-white/[0.06] rounded-lg w-56 mx-auto animate-pulse" />
          <div className="h-3 bg-white/[0.05] rounded-lg w-48 mx-auto animate-pulse" />
          <div className="h-px bg-white/[0.06] w-20 mx-auto" />
        </div>

        {/* Tab nav skeleton */}
        <div className="flex justify-center">
          <div className="flex gap-1 bg-white/[0.04] rounded-xl p-1">
            <div className="h-9 w-24 bg-white/[0.06] rounded-lg animate-pulse" />
            <div className="h-9 w-28 bg-white/[0.04] rounded-lg animate-pulse" />
          </div>
        </div>

        {/* Overall progress card skeleton */}
        <div className="card-surface p-6 space-y-6">
          <div className="h-5 bg-white/[0.06] rounded-lg w-36 animate-pulse" />

          {/* Progress ring placeholder */}
          <div className="flex justify-center">
            <SkeletonCircle size="lg" />
          </div>

          <div className="h-px bg-white/[0.04]" />

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="text-center space-y-2">
                <div className="h-7 bg-white/[0.06] rounded-lg w-12 mx-auto animate-pulse" />
                <div className="h-3 bg-white/[0.04] rounded-lg w-20 mx-auto animate-pulse" />
              </div>
            ))}
          </div>
        </div>

        {/* System progress cards grid */}
        <div className="card-surface p-6 space-y-4">
          <div className="h-5 bg-white/[0.06] rounded-lg w-36 animate-pulse" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        </div>

        {/* Insights skeleton */}
        <div className="card-surface p-6 space-y-4">
          <div className="h-5 bg-white/[0.06] rounded-lg w-44 animate-pulse" />
          <SkeletonText width="3/4" />
          <SkeletonText width="full" />
          <SkeletonText width="1/2" />
        </div>
      </div>
    </div>
  );
}

export default DashboardSkeleton;
