"use client";

import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import ApiStateView from "@/components/shared/ApiStateView";
import PracticeLibrary from "@/components/practice/PracticeLibrary";
import { useApi } from "@/lib/useApi";
import {
  listPracticePacks,
  listPractices,
  type PackResponse,
  type PracticeResponse,
} from "@/lib/api";

function LibraryInner() {
  const packs = useApi<PackResponse[]>((signal) => listPracticePacks(signal), []);
  const practices = useApi<PracticeResponse[]>(
    (signal) => listPractices({ signal }),
    [],
  );

  const loading = packs.loading || practices.loading;
  const error = packs.error ?? practices.error;

  return (
    <main className="min-h-screen px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      <div className="max-w-3xl mx-auto flex flex-col gap-8">
        <header className="flex flex-col gap-2">
          <h1 className="font-display text-2xl sm:text-3xl font-medium text-text">
            Practice library
          </h1>
          <p className="text-sm font-body text-text/50 leading-relaxed max-w-prose">
            Everything available to you, grouped by the pack it came from.
            Open any practice to read what it asks and what it&apos;s holding up.
          </p>
          <Link
            href="/practice"
            className="touch-target inline-flex items-center self-start text-sm font-body text-primary underline underline-offset-4 transition-colors duration-200 hover:text-primary-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded"
          >
            Back to today&apos;s practice
          </Link>
        </header>

        <ApiStateView
          loading={loading}
          error={error}
          loadingText="Loading the library..."
          onRetry={() => {
            packs.refetch();
            practices.refetch();
          }}
        >
          <PracticeLibrary
            packs={packs.data ?? []}
            practices={practices.data ?? []}
          />
        </ApiStateView>
      </div>
    </main>
  );
}

export default function PracticeLibraryPage() {
  return (
    <ProtectedRoute>
      <LibraryInner />
    </ProtectedRoute>
  );
}
