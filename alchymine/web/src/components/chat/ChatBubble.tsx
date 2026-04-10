"use client";

/**
 * ChatBubble — floating overlay entry-point for the Growth Assistant.
 *
 * Renders in three modes driven by ChatContext:
 *
 * - **bubble** — 48 px FAB in the bottom-right corner.
 * - **panel**  — Floating chat window (400×500 px on sm+, full-screen on
 *                mobile).
 * - **split**  — Full-height right rail (40 % of viewport on lg+).
 *
 * The active system key is synced from `usePageContext()` whenever the
 * route changes so the assistant always knows which Alchymine pillar the
 * user is currently browsing.
 */

import { useEffect } from "react";

import { useChatOverlay } from "@/contexts/ChatContext";
import { usePageContext } from "@/hooks/usePageContext";

import ChatPanel from "@/components/chat/ChatPanel";
import ChatSearch from "@/components/chat/ChatSearch";

// ---------------------------------------------------------------------------
// Icon components
// ---------------------------------------------------------------------------

function IconSearch() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path
        fillRule="evenodd"
        d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function IconClose() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
    </svg>
  );
}

function IconExpand() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-4 w-4"
    >
      {/* arrows-pointing-out */}
      <path
        fillRule="evenodd"
        d="M1.75 1h4a.75.75 0 0 1 0 1.5H3.56l3.22 3.22a.75.75 0 0 1-1.06 1.06L2.5 3.56v2.19a.75.75 0 0 1-1.5 0v-4C1 1.34 1.34 1 1.75 1ZM10.25 1a.75.75 0 0 1 0 1.5h-1.19l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 3.56v2.19a.75.75 0 0 1-1.5 0v-4C6.5 1.34 6.84 1 7.25 1h3ZM2.5 12.44l3.22-3.22a.75.75 0 0 1 1.06 1.06L3.56 13.5h2.19a.75.75 0 0 1 0 1.5h-4A.75.75 0 0 1 1 14.25v-4a.75.75 0 0 1 1.5 0v2.19ZM8 12.44l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 13.5h2.19a.75.75 0 0 1 0 1.5H7.25A.75.75 0 0 1 6.5 14.25v-4a.75.75 0 0 1 1.5 0v2.19Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function IconCollapse() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 16"
      fill="currentColor"
      className="h-4 w-4"
    >
      {/* arrows-pointing-in */}
      <path
        fillRule="evenodd"
        d="M6.22 1.22a.75.75 0 0 1 1.06 0l.72.72V.75a.75.75 0 0 1 1.5 0v3.5A.75.75 0 0 1 8.75 5h-3.5a.75.75 0 0 1 0-1.5h1.19L5.5 2.56 4.28 3.78a.75.75 0 0 1-1.06-1.06L6.22 1.22ZM1 7.25A.75.75 0 0 1 1.75 6.5h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V9.56L3.28 10.78a.75.75 0 0 1-1.06-1.06L3.44 8.5H2.5a.75.75 0 0 1-.5-.19V7.25ZM8.75 6.5A.75.75 0 0 1 9.5 7.25v.06l1.22-1.22a.75.75 0 1 1 1.06 1.06L10.56 8.5h1.69a.75.75 0 0 1 0 1.5h-3.5A.75.75 0 0 1 8 9.25v-3a.75.75 0 0 1 .75-.75ZM9.5 12.44l1.22-1.22a.75.75 0 1 1 1.06 1.06L10.56 13.5h1.69a.75.75 0 0 1 0 1.5h-3.5A.75.75 0 0 1 8 14.25v-3.5a.75.75 0 0 1 1.5 0v1.69Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// ChatHeader — shared between panel and split modes
// ---------------------------------------------------------------------------

interface ChatHeaderProps {
  systemKey: string | null;
  mode: "panel" | "split";
  onSearch: () => void;
  onExpand: () => void;
  onCollapse: () => void;
  onClose: () => void;
}

function ChatHeader({
  systemKey,
  mode,
  onSearch,
  onExpand,
  onCollapse,
  onClose,
}: ChatHeaderProps) {
  const systemLabel = systemKey
    ? systemKey.charAt(0).toUpperCase() + systemKey.slice(1)
    : null;

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-white/10 px-4 py-3">
      <span className="font-display text-sm font-medium text-text">
        Growth Assistant
        {systemLabel && (
          <>
            {" · "}
            <span className="text-text/60">{systemLabel}</span>
          </>
        )}
      </span>

      <div className="flex items-center gap-1">
        {/* Search */}
        <button
          type="button"
          aria-label="Search"
          onClick={onSearch}
          className="rounded-lg p-1.5 text-text/50 transition-colors hover:bg-white/5 hover:text-text"
        >
          <IconSearch />
        </button>

        {/* Expand / Collapse — hidden on mobile */}
        {mode === "panel" ? (
          <button
            type="button"
            aria-label="Expand"
            onClick={onExpand}
            className="hidden rounded-lg p-1.5 text-text/50 transition-colors hover:bg-white/5 hover:text-text lg:block"
          >
            <IconExpand />
          </button>
        ) : (
          <button
            type="button"
            aria-label="Collapse"
            onClick={onCollapse}
            className="hidden rounded-lg p-1.5 text-text/50 transition-colors hover:bg-white/5 hover:text-text lg:block"
          >
            <IconCollapse />
          </button>
        )}

        {/* Close */}
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="rounded-lg p-1.5 text-text/50 transition-colors hover:bg-white/5 hover:text-text"
        >
          <IconClose />
        </button>
      </div>
    </header>
  );
}

// ---------------------------------------------------------------------------
// ChatBubble
// ---------------------------------------------------------------------------

export default function ChatBubble() {
  const {
    mode,
    searchOpen,
    systemKey,
    openChat,
    closeChat,
    expandChat,
    collapseChat,
    toggleSearch,
    setSystemKey,
  } = useChatOverlay();

  const { systemKey: pageSystemKey } = usePageContext();

  // Sync the active system from the current page route.
  useEffect(() => {
    setSystemKey(pageSystemKey);
  }, [pageSystemKey, setSystemKey]);

  // ---- Bubble mode -------------------------------------------------------
  if (mode === "bubble") {
    return (
      <button
        type="button"
        aria-label="Open chat"
        onClick={openChat}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary shadow-lg shadow-black/30 transition-transform hover:scale-105 active:scale-95"
      >
        <svg
          aria-hidden
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-6 w-6 text-white"
        >
          <path d="M4.913 2.658c2.075-.27 4.19-.408 6.337-.408 2.147 0 4.262.139 6.337.408 1.922.25 3.291 1.861 3.405 3.727a4.403 4.403 0 0 0-1.032-.211 50.89 50.89 0 0 0-8.42 0c-2.358.196-4.04 2.19-4.04 4.434v4.286a4.47 4.47 0 0 0 2.433 3.984L7.28 21.53A.75.75 0 0 1 6 20.97V18.35a47.6 47.6 0 0 1-1.087-.124C2.99 17.977 1.5 16.26 1.5 14.281V6.385c0-1.866 1.369-3.477 3.413-3.727ZM15.75 7.5c-1.376 0-2.739.057-4.086.169C10.124 7.797 9 9.103 9 10.609v4.285c0 1.507 1.128 2.814 2.67 2.94 1.243.102 2.5.157 3.768.165l2.782 2.781a.75.75 0 0 0 1.28-.53v-2.39l.33-.026c1.542-.125 2.67-1.433 2.67-2.94v-4.286c0-1.505-1.125-2.811-2.664-2.94A49.392 49.392 0 0 0 15.75 7.5Z" />
        </svg>
      </button>
    );
  }

  // ---- Split mode --------------------------------------------------------
  if (mode === "split") {
    return (
      <div className="fixed top-0 right-0 z-50 flex h-full w-full flex-col border-l border-white/10 bg-bg lg:w-[40%]">
        <ChatHeader
          systemKey={systemKey}
          mode="split"
          onSearch={toggleSearch}
          onExpand={expandChat}
          onCollapse={collapseChat}
          onClose={closeChat}
        />
        <div className="flex flex-1 flex-col overflow-hidden">
          {searchOpen ? (
            <ChatSearch systemKey={systemKey} onClose={toggleSearch} />
          ) : (
            <ChatPanel systemKey={systemKey} />
          )}
        </div>
      </div>
    );
  }

  // ---- Panel mode --------------------------------------------------------
  return (
    <div className="fixed bottom-0 right-0 z-50 flex h-full w-full flex-col bg-bg sm:bottom-4 sm:right-4 sm:h-[500px] sm:w-[400px] sm:overflow-hidden sm:rounded-2xl sm:border sm:border-white/10 sm:shadow-2xl sm:shadow-black/40">
      <ChatHeader
        systemKey={systemKey}
        mode="panel"
        onSearch={toggleSearch}
        onExpand={expandChat}
        onCollapse={collapseChat}
        onClose={closeChat}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        {searchOpen ? (
          <ChatSearch systemKey={systemKey} onClose={toggleSearch} />
        ) : (
          <ChatPanel systemKey={systemKey} />
        )}
      </div>
    </div>
  );
}
