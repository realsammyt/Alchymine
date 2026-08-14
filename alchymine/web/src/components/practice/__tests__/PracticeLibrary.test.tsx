import { fireEvent, render, screen, within } from "@testing-library/react";
import PracticeLibrary from "../PracticeLibrary";
import PackAttribution from "../PackAttribution";
import type {
  PackManifest,
  PackResponse,
  PracticeDefinition,
  PracticeResponse,
} from "@/lib/api";

const BUNDLED: PackManifest = {
  schema_version: "2.0",
  pack_id: "alchymine-foundations",
  title: "Foundations",
  summary: "Ten starting practices, two for each of the five capacities.",
  version: "1.0.0",
  license: "CC-BY-NC-SA-4.0",
  attribution: "Alchymine Contributors",
  source_url: null,
  bundled: true,
};

const EXTERNAL: PackManifest = {
  ...BUNDLED,
  pack_id: "borrowed-pack",
  title: "Borrowed Pack",
  summary: "A pack mounted from outside the repo.",
  license: "CC-BY-4.0",
  attribution: "Someone Else",
  source_url: "https://example.org/pack",
  bundled: false,
};

function practice(
  slug: string,
  packId: string,
  overrides: Partial<PracticeDefinition> = {},
): PracticeResponse {
  return {
    pack_id: packId,
    progression_depth: 0,
    practice: {
      slug,
      title: slug.replace(/-/g, " "),
      order: 1,
      summary: `What ${slug} is for.`,
      purposes: ["steadiness"],
      category: "somatic",
      builds_on: [],
      related: [],
      use_when: ["When it applies."],
      description: "The body of the practice.",
      expected_shift: "Something is a little different.",
      applications: ["Somewhere it fits."],
      daily_prompts: ["a", "b", "c"],
      self_check: { failure_mode: "A way it goes wrong.", question: "Did it?" },
      scaffold_note: "What it is holding up.",
      duration_minutes: 5,
      evidence_rating: "D",
      contraindications: [],
      tags: [],
      featured: false,
      ...overrides,
    },
  };
}

const PACKS: PackResponse[] = [
  { manifest: BUNDLED, practice_count: 2 },
  { manifest: EXTERNAL, practice_count: 1 },
];

const PRACTICES: PracticeResponse[] = [
  practice("find-the-floor", "alchymine-foundations"),
  practice("name-the-pattern", "alchymine-foundations", {
    purposes: ["self-knowledge"],
    category: "reflection",
  }),
  practice("borrowed-eyes", "borrowed-pack"),
];

describe("PackAttribution", () => {
  it("surfaces the license and who wrote it", () => {
    render(<PackAttribution manifest={EXTERNAL} />);

    expect(screen.getByText(/CC-BY-4.0/)).toBeInTheDocument();
    expect(screen.getByText(/Someone Else/)).toBeInTheDocument();
  });

  it("links the source as a plain anchor", () => {
    render(<PackAttribution manifest={EXTERNAL} />);

    const link = screen.getByRole("link", { name: /source/i });
    expect(link).toHaveAttribute("href", "https://example.org/pack");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("omits the source link when the pack has no source url", () => {
    render(<PackAttribution manifest={BUNDLED} />);
    expect(screen.queryByRole("link", { name: /source/i })).not.toBeInTheDocument();
  });

  it("still shows license and attribution for a bundled pack", () => {
    render(<PackAttribution manifest={BUNDLED} />);

    expect(screen.getByText(/CC-BY-NC-SA-4.0/)).toBeInTheDocument();
    expect(screen.getByText(/Alchymine Contributors/)).toBeInTheDocument();
  });
});

describe("PracticeLibrary", () => {
  it("renders one section per mounted pack", () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    expect(screen.getByRole("region", { name: /Foundations/ })).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /Borrowed Pack/ }),
    ).toBeInTheDocument();
  });

  it("lists each pack's practices under it", () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    const foundations = screen.getByRole("region", { name: /Foundations/ });
    expect(within(foundations).getByText("find the floor")).toBeInTheDocument();
    expect(
      within(foundations).queryByText("borrowed eyes"),
    ).not.toBeInTheDocument();
  });

  it("shows license and attribution on every pack", () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    expect(screen.getByText(/CC-BY-NC-SA-4.0/)).toBeInTheDocument();
    expect(screen.getByText(/CC-BY-4.0/)).toBeInTheDocument();
  });

  it("expands a practice to its description on demand", async () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    // Every fixture shares a description, so index into the list: the
    // first row is find-the-floor, under the first pack.
    expect(screen.getAllByText("The body of the practice.")[0]).not.toBeVisible();

    fireEvent.click(screen.getAllByRole("button", { name: /find the floor/i })[0]);

    expect(screen.getAllByText("The body of the practice.")[0]).toBeVisible();
  });

  it("keeps the collapsed body free of display utilities", () => {
    // jsdom honours the `hidden` attribute directly, so a Tailwind
    // `flex` on the same element passes every visibility assertion here
    // and still renders the body permanently open in a real browser:
    // preflight's `[hidden] { display: none }` and `.flex` have equal
    // specificity, and `.flex` comes later. Caught by screenshotting the
    // built CSS, pinned here so it stays caught.
    const { container } = render(
      <PracticeLibrary packs={PACKS} practices={PRACTICES} />,
    );

    const collapsed = container.querySelectorAll("[hidden]");
    expect(collapsed.length).toBeGreaterThan(0);
    for (const element of Array.from(collapsed)) {
      expect(element.className).toBe("");
    }
  });

  it("filters to one purpose", async () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: "self-knowledge" } });

    expect(screen.getByText("name the pattern")).toBeInTheDocument();
    expect(screen.queryByText("find the floor")).not.toBeInTheDocument();
  });

  it("explains an empty filter result rather than showing nothing", async () => {
    render(<PracticeLibrary packs={PACKS} practices={PRACTICES} />);

    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: "expression" } });

    expect(screen.getByText(/no practices match/i)).toBeInTheDocument();
  });

  it("shows an empty state when nothing is mounted", () => {
    render(<PracticeLibrary packs={[]} practices={[]} />);

    expect(screen.getByText(/no practice packs/i)).toBeInTheDocument();
  });
});
