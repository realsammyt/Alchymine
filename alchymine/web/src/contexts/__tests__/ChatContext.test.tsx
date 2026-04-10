import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";

import { ChatProvider, useChatOverlay } from "@/contexts/ChatContext";

const wrapper = ({ children }: { children: ReactNode }) => (
  <ChatProvider>{children}</ChatProvider>
);

beforeEach(() => {
  localStorage.clear();
});

describe("ChatContext", () => {
  it("initial mode is bubble", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    expect(result.current.mode).toBe("bubble");
    expect(result.current.searchOpen).toBe(false);
    expect(result.current.systemKey).toBeNull();
  });

  it("openChat transitions to panel", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => {
      result.current.openChat();
    });
    expect(result.current.mode).toBe("panel");
  });

  it("expandChat transitions to split", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => {
      result.current.expandChat();
    });
    expect(result.current.mode).toBe("split");
  });

  it("collapseChat from split returns to panel", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => {
      result.current.expandChat();
    });
    act(() => {
      result.current.collapseChat();
    });
    expect(result.current.mode).toBe("panel");
  });

  it("closeChat returns to bubble and resets searchOpen", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => {
      result.current.openChat();
    });
    act(() => {
      result.current.toggleSearch();
    });
    expect(result.current.searchOpen).toBe(true);
    act(() => {
      result.current.closeChat();
    });
    expect(result.current.mode).toBe("bubble");
    expect(result.current.searchOpen).toBe(false);
  });

  it("toggleSearch flips searchOpen", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    expect(result.current.searchOpen).toBe(false);
    act(() => {
      result.current.toggleSearch();
    });
    expect(result.current.searchOpen).toBe(true);
    act(() => {
      result.current.toggleSearch();
    });
    expect(result.current.searchOpen).toBe(false);
  });

  it("persists last active mode to localStorage", () => {
    const { result } = renderHook(() => useChatOverlay(), { wrapper });
    act(() => {
      result.current.expandChat();
    });
    expect(localStorage.getItem("alchymine:chat-mode")).toBe("split");

    // openChat respects the saved split mode
    act(() => {
      result.current.closeChat();
    });
    act(() => {
      result.current.openChat();
    });
    expect(result.current.mode).toBe("split");
  });
});
