/**
 * usePageContext — unit tests.
 *
 * Mocks Next.js `usePathname` to verify system key derivation for
 * each Alchymine route.
 */

import { renderHook } from "@testing-library/react";

import { usePageContext } from "@/hooks/usePageContext";

// Mock Next.js navigation.
const mockPathname = jest.fn<string, []>();
jest.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

beforeEach(() => {
  mockPathname.mockReset();
});

describe("usePageContext", () => {
  it.each([
    ["/healing", "healing", "Ethical Healing"],
    ["/healing/breathwork", "healing", "Ethical Healing"],
    ["/wealth", "wealth", "Generational Wealth"],
    ["/intelligence", "intelligence", "Personal Intelligence"],
    ["/creative", "creative", "Creative Development"],
    ["/perspective", "perspective", "Perspective Enhancement"],
  ])(
    "maps %s to systemKey=%s, label=%s",
    (pathname, expectedKey, expectedLabel) => {
      mockPathname.mockReturnValue(pathname);
      const { result } = renderHook(() => usePageContext());

      expect(result.current.systemKey).toBe(expectedKey);
      expect(result.current.systemLabel).toBe(expectedLabel);
      expect(result.current.pathname).toBe(pathname);
    },
  );

  it.each(["/chat", "/dashboard", "/profile", "/"])(
    "returns null for non-system page %s",
    (pathname) => {
      mockPathname.mockReturnValue(pathname);
      const { result } = renderHook(() => usePageContext());

      expect(result.current.systemKey).toBeNull();
      expect(result.current.systemLabel).toBeNull();
    },
  );
});
