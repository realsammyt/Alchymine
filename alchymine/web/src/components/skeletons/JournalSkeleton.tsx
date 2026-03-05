"use client";

import { SkeletonText } from "@/components/shared/Skeleton";

const ENTRIES_COUNT = 5;

function JournalEntrySkeleton() {
  return (
    <div className="space-y-2 py-4 border-b border-white/[0.05] last:border-0">
      {/* Date line */}
      <SkeletonText width="1/4" className="h-3" />
      {/* Title */}
      <SkeletonText width="3/4" className="h-5" />
      {/* Body lines */}
      <SkeletonText width="full" className="h-3" />
      <SkeletonText width="full" className="h-3" />
      <SkeletonText width="3/4" className="h-3" />
    </div>
  );
}

/**
 * Skeleton screen for the journal entries list.
 * Shows while journal data is loading.
 */
export function JournalSkeleton() {
  return (
    <div
      className="px-4 sm:px-6 lg:px-8 py-10 sm:py-12"
      aria-busy="true"
      aria-label="Loading journal entries"
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Page header skeleton */}
        <div className="space-y-2">
          <div className="h-3 bg-white/[0.06] rounded-lg w-20 animate-pulse" />
          <div className="h-8 bg-white/[0.06] rounded-lg w-40 animate-pulse" />
        </div>

        {/* Filter/action bar skeleton */}
        <div className="flex items-center justify-between">
          <div className="h-9 w-48 bg-white/[0.04] rounded-xl animate-pulse" />
          <div className="h-9 w-32 bg-white/[0.06] rounded-xl animate-pulse" />
        </div>

        {/* Entry list */}
        <div className="card-surface p-6">
          {Array.from({ length: ENTRIES_COUNT }).map((_, i) => (
            <JournalEntrySkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default JournalSkeleton;
