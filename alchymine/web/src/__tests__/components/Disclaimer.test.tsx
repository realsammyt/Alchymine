import { render, screen } from "@testing-library/react";
import Disclaimer from "@/components/shared/Disclaimer";
import { COPY } from "@/lib/copy";

describe("Disclaimer", () => {
  it("renders the financial disclaimer text", () => {
    render(<Disclaimer type="financial" />);
    expect(screen.getByText(COPY.disclaimers.financial)).toBeInTheDocument();
  });

  it("renders the healing disclaimer text", () => {
    render(<Disclaimer type="healing" />);
    expect(screen.getByText(COPY.disclaimers.healing)).toBeInTheDocument();
  });

  it("renders the biorhythm disclaimer text", () => {
    render(<Disclaimer type="biorhythm" />);
    expect(screen.getByText(COPY.disclaimers.biorhythm)).toBeInTheDocument();
  });

  it("renders the entertainment disclaimer text", () => {
    render(<Disclaimer type="entertainment" />);
    expect(
      screen.getByText(COPY.disclaimers.entertainment),
    ).toBeInTheDocument();
  });

  it("renders all 4 disclaimer types without crashing", () => {
    const types = [
      "financial",
      "healing",
      "biorhythm",
      "entertainment",
    ] as const;
    types.forEach((type) => {
      const { unmount } = render(<Disclaimer type={type} />);
      expect(screen.getByText(COPY.disclaimers[type])).toBeInTheDocument();
      unmount();
    });
  });

  it("includes an info icon (aria-hidden svg)", () => {
    const { container } = render(<Disclaimer type="financial" />);
    const svg = container.querySelector("svg[aria-hidden='true']");
    expect(svg).toBeInTheDocument();
  });

  it("renders as a paragraph element", () => {
    const { container } = render(<Disclaimer type="healing" />);
    const p = container.querySelector("p");
    expect(p).toBeInTheDocument();
  });
});
