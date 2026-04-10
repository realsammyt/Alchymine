# Chat Bubble & Creative Studio UX — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global floating chat bubble with panel/split/search modes, make Creative Studio discoverable via nav + CTA, and fix Gemini Docker config.

**Architecture:** ChatProvider context wraps the app in layout.tsx, managing mode state (bubble/panel/split). ChatBubble component renders per mode, reusing existing ChatPanel internals. ContentWrapper gets a conditional margin class for split-screen reflow. Backend gets `?q=` search and `?ephemeral=true` on existing chat endpoints.

**Tech Stack:** Next.js 15, React 18, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy async

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `alchymine/web/src/contexts/ChatContext.tsx` | ChatProvider: mode state, systemKey sync, open/close/expand/search actions |
| `alchymine/web/src/components/chat/ChatBubble.tsx` | Renders FAB, panel, or split shell around ChatPanel based on mode |
| `alchymine/web/src/components/chat/ChatSearch.tsx` | Search overlay: history search tab + quick-ask tab |
| `alchymine/web/src/components/chat/__tests__/ChatBubble.test.tsx` | ChatBubble mode rendering + transitions |
| `alchymine/web/src/components/chat/__tests__/ChatSearch.test.tsx` | Search tabs, history filtering, quick-ask |
| `alchymine/web/src/contexts/__tests__/ChatContext.test.tsx` | Provider state transitions, localStorage persistence |
| `tests/api/test_chat_search.py` | Backend: `?q=` search and `?ephemeral=true` |

### Modified Files
| File | Change |
|------|--------|
| `alchymine/web/src/app/layout.tsx` | Wrap app in ChatProvider, add ChatBubble |
| `alchymine/web/src/components/shared/ContentWrapper.tsx` | Read chatExpanded from context, apply `mr-[40%]` |
| `alchymine/web/src/components/shared/Navigation.tsx` | Add "Studio" nav item after "Creative" |
| `alchymine/web/src/app/creative/page.tsx` | Add CTA button linking to /creative-studio |
| `alchymine/web/src/lib/chat.ts` | Add `q` param to fetchChatHistory, add `ephemeral` param to streamChat |
| `alchymine/api/routers/chat.py` | Add `?q=` to GET /history, add `?ephemeral=` to POST /chat |
| `infrastructure/docker/Dockerfile.api` | `pip install ".[gemini]"` |
| `infrastructure/docker-compose.yml` | Add GEMINI_API_KEY passthrough |

---

### Task 1: Gemini Docker Hotfix

**Files:**
- Modify: `infrastructure/docker/Dockerfile.api:40`
- Modify: `infrastructure/docker-compose.yml:27-28`

- [ ] **Step 1: Fix Dockerfile to include gemini optional dependency**

In `infrastructure/docker/Dockerfile.api`, change line 40:

```dockerfile
# Before:
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir uvloop httptools

# After:
RUN pip install --no-cache-dir ".[gemini]" && \
    pip install --no-cache-dir uvloop httptools
```

- [ ] **Step 2: Add GEMINI_API_KEY to docker-compose.yml api service**

In `infrastructure/docker-compose.yml`, after the `ANTHROPIC_API_KEY` line (~line 27), add:

```yaml
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
```

- [ ] **Step 3: Commit**

```bash
git add infrastructure/docker/Dockerfile.api infrastructure/docker-compose.yml
git commit -m "fix(infra): include google-genai SDK and GEMINI_API_KEY in Docker build"
```

---

### Task 2: Creative Studio Discoverability

**Files:**
- Modify: `alchymine/web/src/components/shared/Navigation.tsx:17-90`
- Modify: `alchymine/web/src/app/creative/page.tsx:190-202`

- [ ] **Step 1: Write failing test for Studio nav item**

Create or update the Navigation test to check for the Studio link:

```tsx
// In the existing Navigation test file or a new one
import { render, screen } from "@testing-library/react";
import Navigation from "@/components/shared/Navigation";

// Mock usePathname
jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

test("renders Studio nav link", () => {
  render(<Navigation />);
  const link = screen.getByRole("link", { name: /studio/i });
  expect(link).toHaveAttribute("href", "/creative-studio");
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd alchymine/web && npx jest --testPathPattern="Navigation" --no-coverage 2>&1 | tail -5
```

Expected: FAIL — no link with name "studio" found.

- [ ] **Step 3: Add Studio to NAV_ITEMS in Navigation.tsx**

In `alchymine/web/src/components/shared/Navigation.tsx`, find the NAV_ITEMS array. After the "Creative" entry (around line 56), add:

```tsx
  {
    name: "Studio",
    href: "/creative-studio",
    icon: "sparkle",
    label: "Creative Studio — AI image generation",
  },
```

If the `NavIcon` component doesn't have a "sparkle" icon, use "creative" or "star" — check what icons exist in the `NavIcon` switch statement in the same file.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd alchymine/web && npx jest --testPathPattern="Navigation" --no-coverage 2>&1 | tail -5
```

Expected: PASS

- [ ] **Step 5: Add CTA button on /creative page**

In `alchymine/web/src/app/creative/page.tsx`, find the `<header>` section (around line 190). After the closing `</p>` tag (around line 198), add:

```tsx
  <div className="mt-4">
    <Link
      href="/creative-studio"
      className="inline-flex items-center gap-2 px-5 py-2.5 min-h-[44px] bg-gradient-to-r from-primary to-secondary text-white font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-100"
    >
      Open Creative Studio
      <span aria-hidden="true">&rarr;</span>
    </Link>
  </div>
```

Make sure `Link` is imported from `next/link` at the top of the file.

- [ ] **Step 6: Commit**

```bash
git add alchymine/web/src/components/shared/Navigation.tsx alchymine/web/src/app/creative/page.tsx
git commit -m "feat(web): add Studio nav item and CTA on Creative page"
```

---

### Task 3: ChatProvider Context

**Files:**
- Create: `alchymine/web/src/contexts/ChatContext.tsx`
- Create: `alchymine/web/src/contexts/__tests__/ChatContext.test.tsx`

- [ ] **Step 1: Write failing tests for ChatProvider**

```tsx
// alchymine/web/src/contexts/__tests__/ChatContext.test.tsx
import { act, renderHook } from "@testing-library/react";
import { ChatProvider, useChatOverlay } from "@/contexts/ChatContext";

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ChatProvider>{children}</ChatProvider>
);

describe("ChatProvider", () => {
  beforeEach(() => localStorage.clear());

  test("initial mode is bubble", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    expect(result.current.mode).toBe("bubble");
  });

  test("openChat transitions to panel", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    expect(result.current.mode).toBe("panel");
  });

  test("expandChat transitions to split", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    act(() => result.current.expandChat());
    expect(result.current.mode).toBe("split");
  });

  test("collapseChat transitions from split to panel", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    act(() => result.current.expandChat());
    act(() => result.current.collapseChat());
    expect(result.current.mode).toBe("panel");
  });

  test("closeChat transitions to bubble", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    act(() => result.current.closeChat());
    expect(result.current.mode).toBe("bubble");
  });

  test("toggleSearch flips searchOpen", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    expect(result.current.searchOpen).toBe(false);
    act(() => result.current.toggleSearch());
    expect(result.current.searchOpen).toBe(true);
    act(() => result.current.toggleSearch());
    expect(result.current.searchOpen).toBe(false);
  });

  test("persists last active mode to localStorage", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => result.current.openChat());
    act(() => result.current.expandChat());
    expect(localStorage.getItem("alchymine:chat-mode")).toBe("split");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatContext" --no-coverage 2>&1 | tail -5
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement ChatProvider**

```tsx
// alchymine/web/src/contexts/ChatContext.tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";

export type ChatMode = "bubble" | "panel" | "split";

interface ChatOverlayState {
  mode: ChatMode;
  searchOpen: boolean;
  systemKey: string | null;
  openChat: () => void;
  closeChat: () => void;
  expandChat: () => void;
  collapseChat: () => void;
  toggleSearch: () => void;
  setSystemKey: (key: string | null) => void;
}

const ChatContext = createContext<ChatOverlayState | null>(null);

const STORAGE_KEY = "alchymine:chat-mode";

export function ChatProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ChatMode>("bubble");
  const [searchOpen, setSearchOpen] = useState(false);
  const [systemKey, setSystemKey] = useState<string | null>(null);

  // Persist the last active (non-bubble) mode
  useEffect(() => {
    if (mode !== "bubble") {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  }, [mode]);

  const openChat = useCallback(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    setMode(saved === "split" ? "split" : "panel");
  }, []);

  const closeChat = useCallback(() => {
    setMode("bubble");
    setSearchOpen(false);
  }, []);

  const expandChat = useCallback(() => setMode("split"), []);
  const collapseChat = useCallback(() => setMode("panel"), []);
  const toggleSearch = useCallback(() => setSearchOpen((o) => !o), []);

  const value = useMemo(
    () => ({
      mode,
      searchOpen,
      systemKey,
      openChat,
      closeChat,
      expandChat,
      collapseChat,
      toggleSearch,
      setSystemKey,
    }),
    [mode, searchOpen, systemKey, openChat, closeChat, expandChat, collapseChat, toggleSearch],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChatOverlay(): ChatOverlayState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChatOverlay must be used within ChatProvider");
  return ctx;
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatContext" --no-coverage 2>&1 | tail -10
```

Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/contexts/ChatContext.tsx alchymine/web/src/contexts/__tests__/ChatContext.test.tsx
git commit -m "feat(web): add ChatProvider context for overlay mode management"
```

---

### Task 4: ChatBubble Component

**Files:**
- Create: `alchymine/web/src/components/chat/ChatBubble.tsx`
- Create: `alchymine/web/src/components/chat/__tests__/ChatBubble.test.tsx`

- [ ] **Step 1: Write failing tests for ChatBubble**

```tsx
// alchymine/web/src/components/chat/__tests__/ChatBubble.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import ChatBubble from "@/components/chat/ChatBubble";
import { ChatProvider, useChatOverlay } from "@/contexts/ChatContext";

// Mock ChatPanel to avoid pulling in the full chat stack
jest.mock("@/components/chat/ChatPanel", () => {
  return function MockChatPanel({ systemKey }: { systemKey?: string | null }) {
    return <div data-testid="chat-panel">ChatPanel:{systemKey ?? "general"}</div>;
  };
});

jest.mock("@/hooks/usePageContext", () => ({
  usePageContext: () => ({ systemKey: "healing", systemLabel: "Healing", pathname: "/healing" }),
}));

const Wrapper = ({ children }: { children: React.ReactNode }) => (
  <ChatProvider>{children}</ChatProvider>
);

describe("ChatBubble", () => {
  test("renders FAB button in bubble mode", () => {
    render(<ChatBubble />, { wrapper: Wrapper });
    expect(screen.getByRole("button", { name: /open growth assistant/i })).toBeInTheDocument();
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
  });

  test("clicking FAB opens panel with ChatPanel", () => {
    render(<ChatBubble />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /open growth assistant/i }));
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  test("close button returns to bubble", () => {
    render(<ChatBubble />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /open growth assistant/i }));
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open growth assistant/i })).toBeInTheDocument();
  });

  test("expand button switches to split mode", () => {
    render(<ChatBubble />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /open growth assistant/i }));
    fireEvent.click(screen.getByRole("button", { name: /expand/i }));
    // Split mode renders full-height panel
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
  });

  test("syncs systemKey from usePageContext", () => {
    render(<ChatBubble />, { wrapper: Wrapper });
    fireEvent.click(screen.getByRole("button", { name: /open growth assistant/i }));
    expect(screen.getByTestId("chat-panel")).toHaveTextContent("healing");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatBubble" --no-coverage 2>&1 | tail -5
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement ChatBubble**

```tsx
// alchymine/web/src/components/chat/ChatBubble.tsx
"use client";

import { useEffect } from "react";
import ChatPanel from "@/components/chat/ChatPanel";
import { useChatOverlay } from "@/contexts/ChatContext";
import { usePageContext } from "@/hooks/usePageContext";

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

  const pageContext = usePageContext();

  // Sync system key from current page
  useEffect(() => {
    setSystemKey(pageContext.systemKey);
  }, [pageContext.systemKey, setSystemKey]);

  // Bubble mode — just the FAB
  if (mode === "bubble") {
    return (
      <button
        onClick={openChat}
        aria-label="Open Growth Assistant"
        className="fixed bottom-4 right-4 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary to-secondary shadow-lg shadow-primary/30 transition-transform hover:scale-110 active:scale-95"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          className="h-6 w-6 text-white"
        >
          <path d="M4.913 2.658c2.075-.27 4.19-.408 6.337-.408 2.147 0 4.262.139 6.337.408 1.922.25 3.291 1.861 3.405 3.727a4.403 4.403 0 0 0-1.032-.211 50.89 50.89 0 0 0-8.42 0c-2.358.196-4.04 2.19-4.04 4.434v4.286a4.47 4.47 0 0 0 2.433 3.984L7.28 21.53A.75.75 0 0 1 6 20.97V18.35a47.6 47.6 0 0 1-1.087-.124C2.99 17.977 1.5 16.26 1.5 14.281V6.385c0-1.866 1.369-3.477 3.413-3.727ZM15.75 7.5c-1.376 0-2.739.057-4.086.169C10.124 7.797 9 9.103 9 10.609v4.285c0 1.507 1.128 2.814 2.67 2.94 1.243.102 2.5.157 3.768.165l2.782 2.781a.75.75 0 0 0 1.28-.53v-2.39l.33-.026c1.542-.125 2.67-1.433 2.67-2.94v-4.286c0-1.505-1.125-2.811-2.664-2.94A49.392 49.392 0 0 0 15.75 7.5Z" />
        </svg>
      </button>
    );
  }

  // Panel or Split mode
  const isExpanded = mode === "split";

  const panelClasses = isExpanded
    ? "fixed top-0 right-0 z-50 flex h-full w-full flex-col border-l border-white/10 bg-bg lg:w-[40%]"
    : "fixed bottom-0 right-0 z-50 flex h-full w-full flex-col bg-bg sm:bottom-4 sm:right-4 sm:h-[500px] sm:w-[400px] sm:overflow-hidden sm:rounded-2xl sm:border sm:border-white/10 sm:shadow-2xl sm:shadow-black/40";

  return (
    <div className={panelClasses}>
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-white/5 bg-surface/60 px-3 py-2">
        <span className="text-xs font-semibold text-primary">
          Growth Assistant
          {systemKey ? ` \u00b7 ${systemKey.charAt(0).toUpperCase() + systemKey.slice(1)}` : ""}
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={toggleSearch}
            aria-label="Search"
            className="rounded p-1 text-text/40 transition-colors hover:text-text/70"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-4 w-4">
              <path fillRule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clipRule="evenodd" />
            </svg>
          </button>
          {isExpanded ? (
            <button
              onClick={collapseChat}
              aria-label="Collapse"
              className="rounded p-1 text-text/40 transition-colors hover:text-text/70"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-4 w-4">
                <path d="M2.75 9a.75.75 0 0 0 0 1.5h3.69l-4.72 4.72a.75.75 0 1 0 1.06 1.06L7.5 11.56v3.69a.75.75 0 0 0 1.5 0V9H2.75ZM13.25 7a.75.75 0 0 0 0-1.5H9.56l4.72-4.72a.75.75 0 0 0-1.06-1.06L8.5 4.44V.75a.75.75 0 0 0-1.5 0V7h6.25Z" />
              </svg>
            </button>
          ) : (
            <button
              onClick={expandChat}
              aria-label="Expand"
              className="hidden rounded p-1 text-text/40 transition-colors hover:text-text/70 lg:block"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-4 w-4">
                <path d="M5.828 10.172a.75.75 0 0 0-1.06 0l-3.06 3.06V11.5a.75.75 0 0 0-1.5 0v3.25c0 .414.336.75.75.75H4.5a.75.75 0 0 0 0-1.5H2.768l3.06-3.06a.75.75 0 0 0 0-1.06ZM11.5.208a.75.75 0 0 0-.75.75V4.5a.75.75 0 0 0 1.5 0V2.768l3.06 3.06a.75.75 0 0 0 1.06-1.06l-3.06-3.06H15.5a.75.75 0 0 0 0-1.5H11.5Z" />
              </svg>
            </button>
          )}
          <button
            onClick={closeChat}
            aria-label="Close"
            className="rounded p-1 text-text/40 transition-colors hover:text-text/70"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-4 w-4">
              <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22 3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z" />
            </svg>
          </button>
        </div>
      </div>
      {/* Chat content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <ChatPanel systemKey={systemKey} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatBubble" --no-coverage 2>&1 | tail -10
```

Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/components/chat/ChatBubble.tsx alchymine/web/src/components/chat/__tests__/ChatBubble.test.tsx
git commit -m "feat(web): add ChatBubble component with bubble/panel/split modes"
```

---

### Task 5: Wire ChatProvider + ChatBubble into Layout

**Files:**
- Modify: `alchymine/web/src/app/layout.tsx:74-85`
- Modify: `alchymine/web/src/components/shared/ContentWrapper.tsx:1-30`

- [ ] **Step 1: Write failing test for ContentWrapper split reflow**

```tsx
// alchymine/web/src/components/shared/__tests__/ContentWrapper.test.tsx
import { render } from "@testing-library/react";
import ContentWrapper from "@/components/shared/ContentWrapper";

// Mock ChatContext
const mockUseChatOverlay = jest.fn();
jest.mock("@/contexts/ChatContext", () => ({
  useChatOverlay: () => mockUseChatOverlay(),
}));

jest.mock("next/navigation", () => ({
  usePathname: () => "/healing",
}));

describe("ContentWrapper", () => {
  test("applies right margin when chat is in split mode on desktop", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "split" });
    const { container } = render(
      <ContentWrapper><div>Content</div></ContentWrapper>
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain("lg:mr-[40%]");
  });

  test("no right margin when chat is in panel mode", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "panel" });
    const { container } = render(
      <ContentWrapper><div>Content</div></ContentWrapper>
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("lg:mr-[40%]");
  });

  test("no right margin when chat is in bubble mode", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "bubble" });
    const { container } = render(
      <ContentWrapper><div>Content</div></ContentWrapper>
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).not.toContain("lg:mr-[40%]");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd alchymine/web && npx jest --testPathPattern="ContentWrapper" --no-coverage 2>&1 | tail -5
```

Expected: FAIL — useChatOverlay not found or className doesn't match.

- [ ] **Step 3: Update ContentWrapper to read chat mode**

Replace `alchymine/web/src/components/shared/ContentWrapper.tsx`:

```tsx
"use client";

import { usePathname } from "next/navigation";
import { useChatOverlay } from "@/contexts/ChatContext";

const PUBLIC_PAGES = [
  "/",
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
];

export default function ContentWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { mode } = useChatOverlay();
  const isPublic = PUBLIC_PAGES.includes(pathname);

  if (isPublic) {
    return <>{children}</>;
  }

  const splitMargin = mode === "split" ? "lg:mr-[40%]" : "";

  return (
    <div
      className={`lg:ml-64 pt-14 pb-16 lg:pt-0 lg:pb-0 min-h-screen transition-[margin] duration-300 ease-in-out ${splitMargin}`}
    >
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Update layout.tsx to wrap in ChatProvider and render ChatBubble**

In `alchymine/web/src/app/layout.tsx`, add imports:

```tsx
import { ChatProvider } from "@/contexts/ChatContext";
import ChatBubble from "@/components/chat/ChatBubble";
```

Then wrap the body contents inside `<Providers>` with `<ChatProvider>` and add `<ChatBubble />` after `<FeedbackButton />`:

```tsx
<Providers>
  <ChatProvider>
    <a href="#main-content" className="sr-only focus:...">Skip to main content</a>
    <Navigation />
    <ContentWrapper>{children}</ContentWrapper>
    <FeedbackButton />
    <ChatBubble />
  </ChatProvider>
</Providers>
```

- [ ] **Step 5: Run ContentWrapper tests**

```bash
cd alchymine/web && npx jest --testPathPattern="ContentWrapper" --no-coverage 2>&1 | tail -10
```

Expected: 3 tests PASS

- [ ] **Step 6: Run full frontend test suite**

```bash
cd alchymine/web && npm test -- --watchAll=false 2>&1 | tail -10
```

Expected: All tests pass. Some existing tests may need a ChatProvider wrapper — if so, add a mock:

```tsx
jest.mock("@/contexts/ChatContext", () => ({
  useChatOverlay: () => ({ mode: "bubble" }),
  ChatProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
```

- [ ] **Step 7: Commit**

```bash
git add alchymine/web/src/app/layout.tsx alchymine/web/src/components/shared/ContentWrapper.tsx alchymine/web/src/components/shared/__tests__/ContentWrapper.test.tsx
git commit -m "feat(web): wire ChatProvider and ChatBubble into app layout with split reflow"
```

---

### Task 6: Backend — History Search + Ephemeral Chat

**Files:**
- Modify: `alchymine/api/routers/chat.py:320-389,392-439`
- Create: `tests/api/test_chat_search.py`

- [ ] **Step 1: Write failing tests for ?q= search and ?ephemeral=true**

```python
# tests/api/test_chat_search.py
"""Tests for chat history search and ephemeral mode."""

import pytest
from httpx import AsyncClient


class TestChatHistorySearch:
    """GET /api/v1/chat/history?q=<term> filters by content."""

    @pytest.mark.asyncio
    async def test_search_returns_matching_messages(
        self, authed_client: AsyncClient
    ) -> None:
        # Send two messages to create history
        await authed_client.post(
            "/api/v1/chat",
            json={"message": "Tell me about breathwork", "system_key": "healing"},
        )
        await authed_client.post(
            "/api/v1/chat",
            json={"message": "Explain shadow work", "system_key": "healing"},
        )
        resp = await authed_client.get(
            "/api/v1/chat/history", params={"q": "breathwork"}
        )
        assert resp.status_code == 200
        items = resp.json()
        # At least the user message containing "breathwork"
        assert any("breathwork" in item["content"].lower() for item in items)
        # Should NOT include "shadow work" user message
        assert not any(
            "shadow work" in item["content"].lower()
            for item in items
            if item["role"] == "user"
        )

    @pytest.mark.asyncio
    async def test_search_no_matches_returns_empty(
        self, authed_client: AsyncClient
    ) -> None:
        resp = await authed_client.get(
            "/api/v1/chat/history", params={"q": "xyznonexistent"}
        )
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_search_combines_with_system_key(
        self, authed_client: AsyncClient
    ) -> None:
        await authed_client.post(
            "/api/v1/chat",
            json={"message": "budget tips", "system_key": "wealth"},
        )
        # Search for "budget" scoped to healing — should find nothing
        resp = await authed_client.get(
            "/api/v1/chat/history",
            params={"q": "budget", "system_key": "healing"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestEphemeralChat:
    """POST /api/v1/chat?ephemeral=true streams but does not persist."""

    @pytest.mark.asyncio
    async def test_ephemeral_does_not_persist(
        self, authed_client: AsyncClient
    ) -> None:
        # Send ephemeral message
        resp = await authed_client.post(
            "/api/v1/chat",
            json={"message": "What is mindfulness?", "system_key": "healing"},
            params={"ephemeral": "true"},
        )
        assert resp.status_code == 200

        # Check history — ephemeral message should NOT appear
        history = await authed_client.get(
            "/api/v1/chat/history", params={"system_key": "healing"}
        )
        items = history.json()
        assert not any(
            "mindfulness" in item["content"].lower()
            for item in items
            if item["role"] == "user"
        )

    @pytest.mark.asyncio
    async def test_ephemeral_still_enforces_scope(
        self, authed_client: AsyncClient
    ) -> None:
        resp = await authed_client.post(
            "/api/v1/chat",
            json={"message": "Write me a Python script", "system_key": "healing"},
            params={"ephemeral": "true"},
        )
        assert resp.status_code == 400  # Scope enforcement blocks it
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
D:/Python/Python311/python.exe -m pytest tests/api/test_chat_search.py -v 2>&1 | tail -10
```

Expected: FAIL — `?q=` not supported, `?ephemeral=` not supported.

- [ ] **Step 3: Add ?q= parameter to GET /history**

In `alchymine/api/routers/chat.py`, update the `chat_history` function signature to add `q`:

```python
@router.get("/chat/history")
async def chat_history(
    system_key: str | None = Query(None, description="Filter by system"),
    limit: int = Query(50, ge=1, le=200, description="Max messages"),
    q: str | None = Query(None, description="Search message content"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatHistoryItem]:
```

After fetching messages from the DB, add post-query filtering (since content is encrypted, we filter in Python):

```python
    # ... existing query logic ...
    messages = result.scalars().all()

    # Post-query content search (content is encrypted, can't filter in SQL)
    if q:
        q_lower = q.lower()
        messages = [m for m in messages if q_lower in m.content.lower()]

    return [
        ChatHistoryItem(
            id=m.id,
            role=m.role,
            content=m.content,
            system_key=m.system_key,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]
```

- [ ] **Step 4: Add ?ephemeral= parameter to POST /chat**

In `alchymine/api/routers/chat.py`, update the `chat` endpoint signature:

```python
@router.post("/chat")
async def chat(
    request: ChatRequest,
    ephemeral: bool = Query(False, description="Skip message persistence"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
```

Pass `ephemeral` into the internal `_chat_event_stream` generator. Inside that generator, wrap the persist calls in `if not ephemeral:` guards:

```python
    # Before LLM call — persist user message (skip if ephemeral)
    if not ephemeral:
        await repository.save_chat_message(...)

    # ... stream LLM response ...

    # After stream — persist assistant message (skip if ephemeral)
    if not ephemeral:
        await repository.save_chat_message(...)
```

Also skip the history cap check when ephemeral (since we're not persisting).

- [ ] **Step 5: Run tests to verify they pass**

```bash
D:/Python/Python311/python.exe -m pytest tests/api/test_chat_search.py -v 2>&1 | tail -10
```

Expected: 5 tests PASS

- [ ] **Step 6: Run full chat test suite to verify no regressions**

```bash
D:/Python/Python311/python.exe -m pytest tests/api/test_chat.py tests/api/test_chat_search.py -v 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add alchymine/api/routers/chat.py tests/api/test_chat_search.py
git commit -m "feat(api): add history search (?q=) and ephemeral chat mode (?ephemeral=true)"
```

---

### Task 7: Frontend Chat API — Search + Ephemeral

**Files:**
- Modify: `alchymine/web/src/lib/chat.ts:182-218`

- [ ] **Step 1: Add q parameter to fetchChatHistory**

In `alchymine/web/src/lib/chat.ts`, update `fetchChatHistory`:

```tsx
export async function fetchChatHistory(
  systemKey: string | null,
  limit: number = 50,
  q?: string,
): Promise<ChatMessage[]> {
  const params = new URLSearchParams();
  if (systemKey) params.set("system_key", systemKey);
  params.set("limit", String(limit));
  if (q) params.set("q", q);

  // ... rest of fetch logic unchanged, using params.toString() in URL
}
```

- [ ] **Step 2: Add ephemeral parameter to streamChat**

Update the `streamChat` function to accept an optional `ephemeral` flag:

```tsx
export async function* streamChat(
  request: ChatRequest,
  signal?: AbortSignal,
  ephemeral?: boolean,
): AsyncGenerator<string> {
  const url = ephemeral
    ? `${API_BASE}/api/v1/chat?ephemeral=true`
    : `${API_BASE}/api/v1/chat`;

  // ... rest of streaming logic unchanged
}
```

- [ ] **Step 3: Commit**

```bash
git add alchymine/web/src/lib/chat.ts
git commit -m "feat(web): add search and ephemeral params to chat API client"
```

---

### Task 8: ChatSearch Component

**Files:**
- Create: `alchymine/web/src/components/chat/ChatSearch.tsx`
- Create: `alchymine/web/src/components/chat/__tests__/ChatSearch.test.tsx`

- [ ] **Step 1: Write failing tests for ChatSearch**

```tsx
// alchymine/web/src/components/chat/__tests__/ChatSearch.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ChatSearch from "@/components/chat/ChatSearch";

// Mock the chat API
jest.mock("@/lib/chat", () => ({
  fetchChatHistory: jest.fn().mockResolvedValue([
    { id: "1", role: "user", content: "breathwork tips", createdAt: "2026-04-10T00:00:00Z" },
    { id: "2", role: "assistant", content: "Try 4-7-8 breathing", createdAt: "2026-04-10T00:00:01Z" },
  ]),
  streamChat: jest.fn(),
}));

describe("ChatSearch", () => {
  test("renders history and quick-ask tabs", () => {
    render(<ChatSearch systemKey="healing" onClose={() => {}} />);
    expect(screen.getByRole("tab", { name: /history/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /quick ask/i })).toBeInTheDocument();
  });

  test("history tab shows search input", () => {
    render(<ChatSearch systemKey="healing" onClose={() => {}} />);
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
  });

  test("switching to quick-ask tab shows ask input", () => {
    render(<ChatSearch systemKey="healing" onClose={() => {}} />);
    fireEvent.click(screen.getByRole("tab", { name: /quick ask/i }));
    expect(screen.getByPlaceholderText(/ask anything/i)).toBeInTheDocument();
  });

  test("searching history calls fetchChatHistory with q param", async () => {
    const { fetchChatHistory } = require("@/lib/chat");
    render(<ChatSearch systemKey="healing" onClose={() => {}} />);
    const input = screen.getByPlaceholderText(/search/i);
    fireEvent.change(input, { target: { value: "breathwork" } });
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => {
      expect(fetchChatHistory).toHaveBeenCalledWith("healing", 20, "breathwork");
    });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatSearch" --no-coverage 2>&1 | tail -5
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement ChatSearch**

```tsx
// alchymine/web/src/components/chat/ChatSearch.tsx
"use client";

import { FormEvent, useState } from "react";
import { fetchChatHistory } from "@/lib/chat";
import type { ChatMessage } from "@/lib/chat";

interface Props {
  systemKey: string | null;
  onClose: () => void;
}

export default function ChatSearch({ systemKey, onClose }: Props) {
  const [tab, setTab] = useState<"history" | "quickask">("history");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ChatMessage[]>([]);
  const [searching, setSearching] = useState(false);

  async function handleHistorySearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const msgs = await fetchChatHistory(systemKey, 20, query.trim());
      setResults(msgs);
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* Tab bar */}
      <div className="flex border-b border-white/5" role="tablist">
        <button
          role="tab"
          aria-selected={tab === "history"}
          onClick={() => setTab("history")}
          className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
            tab === "history" ? "border-b-2 border-primary text-primary" : "text-text/40 hover:text-text/60"
          }`}
        >
          History
        </button>
        <button
          role="tab"
          aria-selected={tab === "quickask"}
          onClick={() => setTab("quickask")}
          className={`flex-1 px-3 py-2 text-xs font-medium transition-colors ${
            tab === "quickask" ? "border-b-2 border-primary text-primary" : "text-text/40 hover:text-text/60"
          }`}
        >
          Quick Ask
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-3">
        {tab === "history" && (
          <>
            <form onSubmit={handleHistorySearch}>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search past conversations..."
                className="w-full rounded-lg border border-white/10 bg-surface px-3 py-2 text-sm text-text placeholder:text-text/30 focus:border-primary focus:outline-none"
              />
            </form>
            <div className="mt-3 space-y-2">
              {searching && <p className="text-xs text-text/40">Searching...</p>}
              {!searching && results.length === 0 && query && (
                <p className="text-xs text-text/40">No results</p>
              )}
              {results.map((msg) => (
                <div
                  key={msg.id}
                  className="rounded-lg border border-white/5 bg-surface/40 p-2"
                >
                  <span className="text-[10px] font-medium uppercase text-text/30">
                    {msg.role}
                  </span>
                  <p className="mt-0.5 text-xs text-text/70 line-clamp-3">
                    {msg.content}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}

        {tab === "quickask" && (
          <div>
            <input
              type="text"
              placeholder="Ask anything..."
              className="w-full rounded-lg border border-white/10 bg-surface px-3 py-2 text-sm text-text placeholder:text-text/30 focus:border-primary focus:outline-none"
            />
            <p className="mt-2 text-[10px] text-text/30">
              Quick answers — not saved to conversation history.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Wire ChatSearch into ChatBubble**

In `alchymine/web/src/components/chat/ChatBubble.tsx`, import and conditionally render ChatSearch:

```tsx
import ChatSearch from "@/components/chat/ChatSearch";

// Inside the panel/split rendering, replace the ChatPanel section:
{/* Chat content */}
<div className="flex flex-1 flex-col overflow-hidden">
  {searchOpen ? (
    <ChatSearch systemKey={systemKey} onClose={toggleSearch} />
  ) : (
    <ChatPanel systemKey={systemKey} />
  )}
</div>
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd alchymine/web && npx jest --testPathPattern="ChatSearch|ChatBubble" --no-coverage 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 6: Run full frontend suite**

```bash
cd alchymine/web && npm test -- --watchAll=false 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add alchymine/web/src/components/chat/ChatSearch.tsx alchymine/web/src/components/chat/__tests__/ChatSearch.test.tsx alchymine/web/src/components/chat/ChatBubble.tsx
git commit -m "feat(web): add ChatSearch with history search and quick-ask tabs"
```

---

### Task 9: Final Integration + Lint Pass

**Files:**
- All modified files

- [ ] **Step 1: Run full backend test suite**

```bash
D:/Python/Python311/python.exe -m pytest tests/ -v --tb=short 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 2: Run backend lint**

```bash
D:/Python/Python311/python.exe -m ruff check alchymine/ && D:/Python/Python311/python.exe -m ruff format --check alchymine/
```

Fix any issues. Then:

```bash
D:/Python/Python311/python.exe -m mypy alchymine/
```

- [ ] **Step 3: Run full frontend test suite**

```bash
cd alchymine/web && npm test -- --watchAll=false 2>&1 | tail -10
```

Expected: All tests pass.

- [ ] **Step 4: Run frontend lint**

```bash
cd alchymine/web && npm run lint
```

Fix any issues.

- [ ] **Step 5: Final commit and push**

```bash
git add -A
git status  # Review — no .env or secrets
git commit -m "chore: final lint pass for chat bubble + creative studio UX"
git push -u origin feat/chat-bubble-creative-studio-ux
```
