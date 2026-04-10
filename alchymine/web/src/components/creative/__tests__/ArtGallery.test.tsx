import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";

import ArtGallery, { GalleryImage } from "@/components/creative/ArtGallery";

// Mock URL.createObjectURL / revokeObjectURL — jsdom doesn't ship them.
beforeAll(() => {
  global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
  global.URL.revokeObjectURL = jest.fn();
});

beforeEach(() => {
  const mockBlob = new Blob([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], {
    type: "image/png",
  });
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    blob: async () => mockBlob,
  }) as unknown as typeof fetch;
});

afterEach(() => {
  jest.clearAllMocks();
});

const SAMPLE_IMAGES: GalleryImage[] = [
  {
    id: "img-1",
    prompt: "A breathtaking symbolic landscape representing the Sage archetype",
    stylePreset: "mystical",
    createdAt: "2026-04-08T12:00:00Z",
  },
  {
    id: "img-2",
    prompt: "Cosmic illustration with starfields and nebulae swirling at twilight",
    stylePreset: "celestial",
    createdAt: "2026-04-07T18:30:00Z",
  },
];

describe("ArtGallery", () => {
  it("renders the empty state when no images are provided", () => {
    render(<ArtGallery images={[]} />);
    expect(screen.getByTestId("gallery-empty")).toBeInTheDocument();
    expect(
      screen.getByText(/no generated art yet/i),
    ).toBeInTheDocument();
  });

  it("renders one card per image in a grid", async () => {
    await act(async () => {
      render(<ArtGallery images={SAMPLE_IMAGES} />);
    });

    expect(screen.getByTestId("gallery-grid")).toBeInTheDocument();
    // Two open buttons, one per thumbnail.
    await waitFor(() => {
      const buttons = screen.getAllByRole("button", { name: /open image/i });
      expect(buttons).toHaveLength(2);
    });
  });

  it("opens the lightbox when a thumbnail is clicked", async () => {
    await act(async () => {
      render(<ArtGallery images={SAMPLE_IMAGES} />);
    });

    const firstThumb = (
      await screen.findAllByRole("button", { name: /open image/i })
    )[0];
    await act(async () => {
      fireEvent.click(firstThumb);
    });

    await waitFor(() => {
      expect(screen.getByTestId("art-lightbox")).toBeInTheDocument();
    });
    // Lightbox shows the prompt text.
    expect(
      screen.getByTestId("lightbox-prompt").textContent,
    ).toContain("Sage archetype");
    // Style badge is visible.
    expect(screen.getByTestId("lightbox-style-badge")).toHaveTextContent(
      /mystical/i,
    );
  });

  it("closes the lightbox on ESC", async () => {
    await act(async () => {
      render(<ArtGallery images={SAMPLE_IMAGES} />);
    });

    const firstThumb = (
      await screen.findAllByRole("button", { name: /open image/i })
    )[0];
    await act(async () => {
      fireEvent.click(firstThumb);
    });
    await waitFor(() => {
      expect(screen.getByTestId("art-lightbox")).toBeInTheDocument();
    });

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByTestId("art-lightbox")).not.toBeInTheDocument();
    });
  });

  it("closes the lightbox when the overlay is clicked", async () => {
    await act(async () => {
      render(<ArtGallery images={SAMPLE_IMAGES} />);
    });

    const firstThumb = (
      await screen.findAllByRole("button", { name: /open image/i })
    )[0];
    await act(async () => {
      fireEvent.click(firstThumb);
    });
    const overlay = await screen.findByTestId("art-lightbox");

    // Click on the overlay itself (the outer element).
    fireEvent.click(overlay);

    await waitFor(() => {
      expect(screen.queryByTestId("art-lightbox")).not.toBeInTheDocument();
    });
  });

  it("renders a Delete button per card when onDelete is provided", async () => {
    const onDelete = jest.fn();
    await act(async () => {
      render(<ArtGallery images={SAMPLE_IMAGES} onDelete={onDelete} />);
    });

    const deleteButtons = await screen.findAllByRole("button", {
      name: /delete image generated from prompt/i,
    });
    expect(deleteButtons).toHaveLength(2);

    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith("img-1");
  });
});
