/**
 * ContentWrapper — component tests.
 *
 * Covers the split-mode right-margin reflow behaviour driven by ChatContext.
 */

import { render, screen } from "@testing-library/react";

import ContentWrapper from "@/components/shared/ContentWrapper";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseChatOverlay = jest.fn();
jest.mock("@/contexts/ChatContext", () => ({
  useChatOverlay: () => mockUseChatOverlay(),
}));

jest.mock("next/navigation", () => ({
  usePathname: () => "/healing",
}));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ContentWrapper", () => {
  it("applies lg:mr-[40%] when chat is in split mode", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "split" });

    const { container } = render(<ContentWrapper>content</ContentWrapper>);

    // The wrapper div is the first child of the render container
    const wrapper = container.firstElementChild;
    // Use className string check because toHaveClass treats brackets as regex
    expect(wrapper?.className).toContain("lg:mr-[40%]");
  });

  it("does not apply right margin when chat is in panel mode", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "panel" });

    const { container } = render(<ContentWrapper>content</ContentWrapper>);

    const wrapper = container.firstElementChild;
    expect(wrapper?.className).not.toContain("lg:mr-[40%]");
  });

  it("does not apply right margin when chat is in bubble mode", () => {
    mockUseChatOverlay.mockReturnValue({ mode: "bubble" });

    const { container } = render(<ContentWrapper>content</ContentWrapper>);

    const wrapper = container.firstElementChild;
    expect(wrapper?.className).not.toContain("lg:mr-[40%]");
  });
});
