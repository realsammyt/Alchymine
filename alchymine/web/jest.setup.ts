import "@testing-library/jest-dom";

// jsdom 20 ships without TextEncoder / TextDecoder on the globals.
// The chat SSE client uses TextDecoder at runtime, and the chat hook
// tests construct a TextEncoder for their stream shim, so we polyfill
// both from node:util before any module under test imports them.  We
// cast through ``unknown`` because the node:util versions expose a
// slightly wider type surface than the DOM ``lib.dom.d.ts`` versions
// in newer TypeScript releases.
import {
  TextDecoder as NodeTextDecoder,
  TextEncoder as NodeTextEncoder,
} from "util";

const globalAny = globalThis as unknown as Record<string, unknown>;
if (typeof globalAny.TextEncoder === "undefined") {
  globalAny.TextEncoder = NodeTextEncoder;
}
if (typeof globalAny.TextDecoder === "undefined") {
  globalAny.TextDecoder = NodeTextDecoder;
}

// Mock IntersectionObserver for framer-motion whileInView support in jsdom
class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = "";
  readonly thresholds: ReadonlyArray<number> = [];
  constructor(
    private callback: IntersectionObserverCallback,
    _options?: IntersectionObserverInit,
  ) {
    // Immediately trigger with all entries as intersecting
    setTimeout(() => {
      this.callback(
        [
          { isIntersecting: true, intersectionRatio: 1 },
        ] as IntersectionObserverEntry[],
        this,
      );
    }, 0);
  }
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

Object.defineProperty(window, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

Object.defineProperty(global, "IntersectionObserver", {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});
