"use client";

import { useEffect, useRef, type RefObject } from "react";

/**
 * Focus an element the moment a condition becomes true.
 *
 * This exists because of WCAG 2.4.3. When a control the user is standing
 * on gets replaced by the thing it produced, focus falls to `<body>` and
 * a keyboard user is dropped back to the top of the document with no
 * idea what happened. Moving focus onto the replacement keeps them where
 * they were.
 *
 * It deliberately does nothing on the first render, whatever *active*
 * says. Focusing on mount would yank the page around for a card that
 * simply happens to load in a settled state.
 *
 * The target needs `tabIndex={-1}` to be focusable at all, which makes it
 * programmatically focusable without adding it to the tab order.
 */
export function useFocusOnEnter<T extends HTMLElement>(
  active: boolean,
): RefObject<T> {
  const ref = useRef<T>(null);
  const previous = useRef<boolean | null>(null);

  useEffect(() => {
    if (previous.current === false && active) {
      ref.current?.focus();
    }
    previous.current = active;
  }, [active]);

  return ref;
}
