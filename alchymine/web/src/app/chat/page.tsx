"use client";

/**
 * /chat — dedicated full-viewport Growth Assistant page.
 *
 * Sprint 2 deliverable: a simple protected layout containing a single
 * ``ChatPanel`` in its general (``systemKey=null``) mode.  Pillar-
 * scoped chat and history loading land in Sprint 3 (#164).
 */

import Link from "next/link";

import ChatPanel from "@/components/chat/ChatPanel";
import ProtectedRoute from "@/components/shared/ProtectedRoute";

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <main className="flex min-h-screen flex-col bg-bg">
        <header className="border-b border-white/5 bg-surface/40 px-4 py-3">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-body text-text/60 transition-colors hover:bg-white/5 hover:text-text"
            >
              <svg
                aria-hidden
                viewBox="0 0 24 24"
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="19" y1="12" x2="5" y2="12" />
                <polyline points="12 19 5 12 12 5" />
              </svg>
              Back to dashboard
            </Link>
            <span className="font-display text-sm text-primary/80">
              Growth Assistant
            </span>
          </div>
        </header>

        <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 py-4 sm:py-6">
          <div className="flex h-[calc(100vh-9rem)] flex-col sm:h-[calc(100vh-10rem)]">
            <ChatPanel systemKey={null} />
          </div>
        </div>
      </main>
    </ProtectedRoute>
  );
}
