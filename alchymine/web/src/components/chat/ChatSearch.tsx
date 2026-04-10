"use client";

/**
 * ChatSearch — search overlay rendered inside the chat panel area.
 *
 * Two tabs:
 *  - History  — searches persisted chat history via fetchChatHistory
 *  - Quick Ask — UI shell for ephemeral questions (streaming deferred)
 */

import { useState } from "react";
import type { FormEvent } from "react";

import { fetchChatHistory } from "@/lib/chat";
import type { ChatMessage } from "@/lib/chat";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  systemKey: string | null;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Tab type
// ---------------------------------------------------------------------------

type Tab = "history" | "quickask";

// ---------------------------------------------------------------------------
// ChatSearch
// ---------------------------------------------------------------------------

export default function ChatSearch({ systemKey, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("history");

  // History tab state
  const [historyQuery, setHistoryQuery] = useState("");
  const [results, setResults] = useState<ChatMessage[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  // Quick Ask tab state
  const [quickQuery, setQuickQuery] = useState("");

  const handleHistorySubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!historyQuery.trim()) return;
    setSearching(true);
    setSearched(false);
    try {
      const msgs = await fetchChatHistory(systemKey, 20, historyQuery.trim());
      setResults(msgs);
    } finally {
      setSearching(false);
      setSearched(true);
    }
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Tab bar */}
      <div
        role="tablist"
        className="flex shrink-0 border-b border-white/10 px-4"
      >
        <button
          role="tab"
          type="button"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
          className={
            "mr-4 py-3 text-sm font-body transition-colors " +
            (activeTab === "history"
              ? "border-b-2 border-primary text-primary"
              : "text-text/50 hover:text-text/80")
          }
        >
          History
        </button>
        <button
          role="tab"
          type="button"
          aria-selected={activeTab === "quickask"}
          onClick={() => setActiveTab("quickask")}
          className={
            "py-3 text-sm font-body transition-colors " +
            (activeTab === "quickask"
              ? "border-b-2 border-primary text-primary"
              : "text-text/50 hover:text-text/80")
          }
        >
          Quick Ask
        </button>

        {/* Close button */}
        <button
          type="button"
          aria-label="Close search"
          onClick={onClose}
          className="ml-auto self-center rounded-lg p-1.5 text-text/50 transition-colors hover:bg-white/5 hover:text-text"
        >
          <svg
            aria-hidden
            viewBox="0 0 16 16"
            fill="currentColor"
            className="h-4 w-4"
          >
            <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
          </svg>
        </button>
      </div>

      {/* Tab panels */}
      {activeTab === "history" ? (
        <div className="flex flex-1 flex-col overflow-hidden p-4">
          {/* Search form */}
          <form onSubmit={(e) => void handleHistorySubmit(e)} className="mb-4">
            <input
              type="search"
              value={historyQuery}
              onChange={(e) => setHistoryQuery(e.target.value)}
              placeholder="Search past conversations..."
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-body text-text placeholder-text/40 outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
            />
          </form>

          {/* Results area */}
          <div className="flex-1 overflow-y-auto">
            {searching ? (
              <p className="text-center text-sm font-body text-text/50">
                Searching...
              </p>
            ) : searched && results.length === 0 ? (
              <p className="text-center text-sm font-body text-text/50">
                No results
              </p>
            ) : (
              <ul className="space-y-2">
                {results.map((msg) => (
                  <li
                    key={msg.id}
                    className="rounded-lg border border-white/5 bg-white/5 px-3 py-2"
                  >
                    <p className="mb-1 text-xs font-body font-medium capitalize text-text/50">
                      {msg.role}
                    </p>
                    <p className="line-clamp-3 text-sm font-body text-text/80">
                      {msg.content}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col p-4">
          {/* Quick Ask input */}
          <input
            type="text"
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            placeholder="Ask anything..."
            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm font-body text-text placeholder-text/40 outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/30"
          />
          <p className="mt-2 text-xs font-body text-text/40">
            Quick answers — not saved to conversation history.
          </p>
        </div>
      )}
    </div>
  );
}
