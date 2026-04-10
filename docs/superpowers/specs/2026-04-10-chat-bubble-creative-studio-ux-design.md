# Chat Bubble & Creative Studio UX — Design Spec

**Date:** 2026-04-10
**Status:** Approved
**Scope:** Global chat overlay, Creative Studio discoverability, Gemini Docker fix

---

## Problem

1. The Growth Assistant chat (`/chat`) and Creative Studio (`/creative-studio`) are orphaned pages with no navigation links — users can only reach them via direct URL.
2. Image generation in Creative Studio shows "offline" because the Docker image lacks the `google-genai` SDK (optional dep not installed) and `GEMINI_API_KEY` isn't passed through `docker-compose.yml`.
3. There is no persistent, contextually aware chat experience — the assistant should be accessible from any page without navigating away.

## Solution

### 1. Global Chat Bubble (Approach: Lightweight Overlay)

A floating chat bubble renders on every authenticated page. It has three modes with smooth transitions between them.

#### Modes

| Mode | Trigger | Layout |
|------|---------|--------|
| **Bubble** | Default state | 48px FAB button, bottom-right corner |
| **Panel** | Click bubble | Fixed-position popup, ~400px wide, animates up from corner |
| **Split** | Click expand (⤢) in panel | Page content reflows left, chat takes right ~40-50% full-height |

**Transitions:**
- Bubble → click → Panel (animate up)
- Panel → expand (⤢) → Split (page reflows, chat expands full-height)
- Split → collapse (⤡) → Panel (page reflows back)
- Panel/Split → close (✕) → Bubble
- Any mode → search (🔍) → Search overlay within panel/split

#### Contextual Awareness

On open, the bubble automatically scopes to the current system page via `usePageContext` (already implemented in #164). It shows that system's starter prompts from the existing `starterPrompts.ts`. No pre-loaded context injection at launch — just scope + starters. Context injection is a future enhancement.

Switching pages while chat is open keeps the chat open. System key updates automatically. Conversation resets only on explicit system switch — navigating between pages of the same system keeps the thread.

#### Search Mode

Dual-purpose search accessible from Panel or Split mode header:
- **History tab:** Search past conversation messages. Hits existing `GET /api/v1/chat/history` with a new `?q=` query parameter for text search.
- **Quick Ask tab:** One-shot question without conversation context. Sends message with `?ephemeral=true` query param, gets streamed response, does not persist either message to `chat_messages` table.

#### Responsive Behavior

| Breakpoint | Behavior |
|-----------|----------|
| Mobile (< 768px) | Bubble → Panel only. Panel renders as full-screen modal overlay. No split mode. Expand button hidden. |
| Tablet (768-1024px) | Split available. Chat overlays page content (~50% width) rather than reflowing it. |
| Desktop (> 1024px) | Full split with page content reflow. |

#### Persistence

Chat mode preference (panel vs split) saved to `localStorage` so it remembers the user's preferred working mode across sessions.

### 2. Component Architecture

```
layout.tsx
├── ChatProvider (context: mode, systemKey, open/close/expand)
│   ├── ContentWrapper (existing — gets chatExpanded class for split reflow)
│   └── ChatBubble (new — renders based on mode)
│       ├── mode="bubble" → FAB button only
│       ├── mode="panel" → fixed-position chat panel
│       ├── mode="split" → full-height panel
│       └── ChatSearch (new — overlay within panel/split)
```

**`ChatProvider`** (`alchymine/web/src/contexts/ChatContext.tsx`)
- State: `mode` (bubble | panel | split), `systemKey`, `searchOpen`
- Syncs `systemKey` from `usePageContext` on route change
- Exposes: `openChat()`, `closeChat()`, `expandChat()`, `collapseChat()`, `toggleSearch()`
- Saves mode preference to `localStorage`

**`ChatBubble`** (`alchymine/web/src/components/chat/ChatBubble.tsx`)
- Single component rendering per mode
- Reuses existing `ChatPanel` internals (ChatMessageList, ChatInput, starter prompts) — not a rewrite
- Panel mode: `fixed bottom-4 right-4 w-[400px] h-[500px]` with rounded corners, shadow
- Split mode: `fixed top-0 right-0 h-full w-[40%]` with border-left
- Bubble mode: just the FAB button with gradient + chat icon

**`ChatSearch`** (`alchymine/web/src/components/chat/ChatSearch.tsx`)
- Renders as overlay within the chat panel area
- Two tabs: History (search input + results list) and Quick Ask (single input + response)
- History search: `GET /api/v1/chat/history?q=<term>&limit=20`
- Quick Ask: fires `POST /api/v1/chat?ephemeral=true` — streams response inline, does not persist to DB

**`ContentWrapper`** (existing, modified)
- Accepts `chatExpanded` prop from ChatProvider context
- Desktop (> 1024px): adds `mr-[40%]` when chat is in split mode, triggering page reflow
- Tablet: no reflow (chat overlays)
- Transition: `transition-[margin] duration-300 ease-in-out` for smooth reflow

### 3. Backend Change

Two additions to existing endpoints in `alchymine/api/routers/chat.py`:

**History search** — `GET /api/v1/chat/history`:
- New optional query parameter: `q: str | None = None`
- Encrypted content column means search runs on decrypted values in Python, not SQL — filter post-query after fetching within `system_key` and `limit` constraints

**Ephemeral mode** — `POST /api/v1/chat`:
- New optional query parameter: `ephemeral: bool = False`
- When true, skips persisting user and assistant messages to `chat_messages` table
- Still runs safety check and scope enforcement
- Still streams SSE response identically

### 4. Creative Studio Discoverability

**Navigation item** — Add "Studio" entry to `NAV_ITEMS` in `Navigation.tsx`:
- Position: after "Creative" in the sidebar
- Icon: sparkle or paintbrush (matching design system)
- Path: `/creative-studio`

**CTA on `/creative` page** — Add "Open Creative Studio" button in the hero/header section of the Creative system page, linking to `/creative-studio`.

### 5. Gemini Docker Fix (Hotfix)

**`infrastructure/docker/Dockerfile.api`:**
- Change `pip install --no-cache-dir .` to `pip install --no-cache-dir ".[gemini]"` so the optional `google-genai` SDK is included in the production image.

**`infrastructure/docker-compose.yml`:**
- Add `GEMINI_API_KEY=${GEMINI_API_KEY:-}` to the api service environment block (already added to worker service).

### 6. Testing Strategy

**Frontend tests:**
- `ChatProvider`: mode transitions, systemKey sync, localStorage persistence
- `ChatBubble`: renders correct UI per mode, FAB click opens panel, expand/collapse/close
- `ChatSearch`: tab switching, history search results display, quick ask flow
- `ContentWrapper`: reflow class applied when chatExpanded, removed when collapsed
- `Navigation`: Studio link renders, links to correct path

**Backend tests:**
- `GET /api/v1/chat/history?q=breathwork` returns filtered results
- `?q=` with no matches returns empty list
- `?q=` combined with `?system_key=` filters both
- `POST /api/v1/chat?ephemeral=true` streams response but history endpoint shows no new messages
- Ephemeral mode still enforces scope check and safety check

**No E2E changes** — the existing E2E smoke test from #165 covers the chat flow. New tests focus on the overlay mechanics and search.

### 7. Out of Scope

- Pre-loaded context injection (B/C from brainstorming) — future enhancement
- Proactive suggestions — future enhancement
- Voice input — not planned
- Chat history export — not planned
- SystemCoachBanner removal — stays as-is, coexists with the global bubble
