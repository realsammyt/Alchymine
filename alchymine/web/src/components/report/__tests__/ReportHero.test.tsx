import { render, screen, waitFor, act } from "@testing-library/react";

import ReportHero from "@/components/report/ReportHero";

// Mock URL.createObjectURL / revokeObjectURL — jsdom doesn't ship them.
beforeAll(() => {
  global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
  global.URL.revokeObjectURL = jest.fn();
});

afterEach(() => {
  jest.clearAllMocks();
});

describe("ReportHero", () => {
  it("renders the loading skeleton on initial render", async () => {
    // fetch returns a never-resolving promise so we stay in loading
    global.fetch = jest.fn(
      () => new Promise(() => {}),
    ) as unknown as typeof fetch;

    render(<ReportHero reportId="report-1" userId="user-1" />);
    expect(
      screen.getByLabelText(/generating personalized illustration/i),
    ).toBeInTheDocument();
  });

  it("renders the placeholder when the API returns 204", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => ({}),
    }) as unknown as typeof fetch;

    render(<ReportHero reportId="report-1" userId="user-1" />);

    await waitFor(() => {
      expect(
        screen.getByLabelText(/personalized illustration placeholder/i),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText(/personalized art unavailable/i),
    ).toBeInTheDocument();
  });

  it("renders the image and a regenerate button on 201", async () => {
    const mockBlob = new Blob([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], {
      type: "image/png",
    });

    global.fetch = jest
      .fn()
      // First call: POST /art/generate
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          image_id: "img-123",
          url: "/api/v1/art/img-123",
          prompt: "A breathtaking symbolic landscape representing the Sage",
        }),
      })
      // Second call: GET /art/img-123 (the bytes)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        blob: async () => mockBlob,
      }) as unknown as typeof fetch;

    await act(async () => {
      render(<ReportHero reportId="report-1" userId="user-1" />);
    });

    await waitFor(() => {
      const img = screen.getByRole("img", {
        name: /personalized symbolic illustration/i,
      });
      expect(img).toBeInTheDocument();
      expect((img as HTMLImageElement).src).toBe("blob:mock-url");
    });

    expect(
      screen.getByRole("button", {
        name: /regenerate personalized illustration/i,
      }),
    ).toBeInTheDocument();
  });
});
