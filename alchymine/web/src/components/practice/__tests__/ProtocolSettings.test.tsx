import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ProtocolSettings from "../ProtocolSettings";
import {
  ApiError,
  getEcologySettings,
  listPracticePacks,
  updateEcologySettings,
  type EcologySettings,
  type PackResponse,
} from "@/lib/api";

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    getEcologySettings: jest.fn(),
    listPracticePacks: jest.fn(),
    updateEcologySettings: jest.fn(),
  };
});

const mockGet = getEcologySettings as jest.Mock;
const mockPacks = listPracticePacks as jest.Mock;
const mockUpdate = updateEcologySettings as jest.Mock;

// ─── Fixtures ────────────────────────────────────────────────────────

function pack(packId: string, title: string): PackResponse {
  return {
    manifest: {
      schema_version: "1.0",
      pack_id: packId,
      title,
      summary: "One line about the pack.",
      version: "1.0.0",
      license: "CC-BY-NC-SA-4.0",
      attribution: "Alchymine",
      source_url: null,
      bundled: true,
    },
    practice_count: 4,
  };
}

const FOUNDATIONS = "alchymine-foundations";
const SOMATIC = "somatic-basics";
const PACKS = [pack(FOUNDATIONS, "Foundations"), pack(SOMATIC, "Somatic basics")];

function settings(overrides: Partial<EcologySettings> = {}): EcologySettings {
  return { protocol_size: 3, active_pack_ids: null, ...overrides };
}

const TOGGLE = /protocol settings/i;
const SAVE = /save settings/i;
const ALL_PACKS = /all packs/i;
const PICK_PACKS = /only the packs i pick/i;

/** Let every settled promise in the component's chain land. */
async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

/** Render, open the disclosure, and wait for the form to arrive. */
async function openSettings(onSaved?: () => void) {
  const view = render(<ProtocolSettings onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: TOGGLE }));
  await screen.findByRole("combobox", { name: /practices a day/i });
  return view;
}

function sizeSelect() {
  return screen.getByRole("combobox", { name: /practices a day/i });
}

function saveButton() {
  return screen.getByRole("button", { name: SAVE });
}

beforeEach(() => {
  mockGet.mockReset();
  mockPacks.mockReset();
  mockUpdate.mockReset();
  mockGet.mockResolvedValue(settings());
  mockPacks.mockResolvedValue(PACKS);
  mockUpdate.mockResolvedValue(settings());
});

// ─── Reading what is stored ──────────────────────────────────────────

describe("ProtocolSettings reads", () => {
  it("asks for nothing until it is opened", async () => {
    render(<ProtocolSettings />);

    await flush();
    expect(mockGet).not.toHaveBeenCalled();
    expect(mockPacks).not.toHaveBeenCalled();
  });

  it("shows the stored size and the stored pack choice", async () => {
    mockGet.mockResolvedValue(settings({ protocol_size: 5 }));
    await openSettings();

    expect(sizeSelect()).toHaveValue("5");
    expect(screen.getByRole("radio", { name: ALL_PACKS })).toBeChecked();
  });

  it("shows a stored subset as the packs it names", async () => {
    mockGet.mockResolvedValue(settings({ active_pack_ids: [FOUNDATIONS] }));
    await openSettings();

    expect(screen.getByRole("radio", { name: PICK_PACKS })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /foundations/i })).toBeChecked();
    expect(
      screen.getByRole("checkbox", { name: /somatic basics/i }),
    ).not.toBeChecked();
  });

  it("keeps an unsaved edit when the panel is closed and opened again", async () => {
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "7" } });

    const toggle = screen.getByRole("button", { name: TOGGLE });
    fireEvent.click(toggle);
    fireEvent.click(toggle);

    expect(sizeSelect()).toHaveValue("7");
    expect(mockGet).toHaveBeenCalledTimes(1);
  });

  it("offers another go when the settings will not load", async () => {
    mockGet.mockRejectedValue(new Error("network"));
    render(<ProtocolSettings />);
    fireEvent.click(screen.getByRole("button", { name: TOGGLE }));

    const retry = await screen.findByRole("button", { name: /try again/i });
    mockGet.mockResolvedValue(settings({ protocol_size: 4 }));
    fireEvent.click(retry);

    expect(await screen.findByRole("combobox")).toHaveValue("4");
  });

  it("says so when no packs are mounted", async () => {
    mockPacks.mockResolvedValue([]);
    await openSettings();

    expect(screen.getByText(/no practice packs are mounted/i)).toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });
});

// ─── Saving ──────────────────────────────────────────────────────────

describe("ProtocolSettings saves", () => {
  it("sends the size on its own when only the size changed", async () => {
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "6" } });
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ protocol_size: 6 }),
    );
  });

  it("sends the packs on their own when only the packs changed", async () => {
    await openSettings();
    fireEvent.click(screen.getByRole("radio", { name: PICK_PACKS }));
    fireEvent.click(screen.getByRole("checkbox", { name: /foundations/i }));
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({
        active_pack_ids: [FOUNDATIONS],
      }),
    );
  });

  it("sends null for every mounted pack", async () => {
    // Null is a real value on this route, not an absence: it is how the
    // user says "draw on everything", including packs mounted later.
    mockGet.mockResolvedValue(settings({ active_pack_ids: [FOUNDATIONS] }));
    await openSettings();
    fireEvent.click(screen.getByRole("radio", { name: ALL_PACKS }));
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({ active_pack_ids: null }),
    );
  });

  it("sends both when both changed", async () => {
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("radio", { name: PICK_PACKS }));
    fireEvent.click(screen.getByRole("checkbox", { name: /somatic basics/i }));
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(mockUpdate).toHaveBeenCalledWith({
        protocol_size: 7,
        active_pack_ids: [SOMATIC],
      }),
    );
  });

  it("stays inert while nothing has changed", async () => {
    await openSettings();

    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(saveButton());
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("blocks a save with no packs picked, and says why", async () => {
    // The server refuses an empty list too. This is here so the answer
    // arrives while the user is still looking at the boxes.
    mockGet.mockResolvedValue(settings({ active_pack_ids: [FOUNDATIONS] }));
    await openSettings();
    fireEvent.click(screen.getByRole("checkbox", { name: /foundations/i }));

    expect(
      await screen.findByText(/pick at least one pack/i),
    ).toBeInTheDocument();
    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(saveButton());
    expect(mockUpdate).not.toHaveBeenCalled();
  });

  it("says the save landed and asks the page to read today again", async () => {
    const onSaved = jest.fn();
    mockUpdate.mockResolvedValue(settings({ protocol_size: 6 }));
    await openSettings(onSaved);
    fireEvent.change(sizeSelect(), { target: { value: "6" } });
    fireEvent.click(saveButton());

    expect(await screen.findByText(/^saved\./i)).toBeInTheDocument();
    expect(onSaved).toHaveBeenCalledTimes(1);
    // The saved value is the new baseline, so the form is no longer dirty.
    expect(saveButton()).toHaveAttribute("aria-disabled", "true");
  });

  it("takes the server's answer as the new baseline", async () => {
    // The server sorts and deduplicates the ids, so what came back is
    // the canonical version of the choice. Keeping what was sent would
    // leave the form looking unsaved.
    mockUpdate.mockResolvedValue(
      settings({ active_pack_ids: [FOUNDATIONS, SOMATIC] }),
    );
    await openSettings();
    fireEvent.click(screen.getByRole("radio", { name: PICK_PACKS }));
    fireEvent.click(screen.getByRole("checkbox", { name: /somatic basics/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /foundations/i }));
    fireEvent.click(saveButton());

    await waitFor(() =>
      expect(saveButton()).toHaveAttribute("aria-disabled", "true"),
    );
    expect(screen.getByRole("checkbox", { name: /foundations/i })).toBeChecked();
  });

  it("shows the server's refusal exactly as written", async () => {
    const detail =
      "No mounted pack has the id 'ghost-pack'. See /api/v1/practices/packs for what is mounted.";
    mockUpdate.mockRejectedValue(new ApiError(422, detail));
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "4" } });
    fireEvent.click(saveButton());

    expect(await screen.findByText(detail)).toBeInTheDocument();
  });

  it("offers another go when the save could not be sent", async () => {
    mockUpdate.mockRejectedValue(new Error("network"));
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "4" } });
    fireEvent.click(saveButton());

    expect(await screen.findByText(/didn't save/i)).toBeInTheDocument();
    // Still dirty, so the user can try the same save again.
    expect(saveButton()).toHaveAttribute("aria-disabled", "false");
  });

  it("clears the last verdict once the form changes again", async () => {
    mockUpdate.mockRejectedValue(new Error("network"));
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "4" } });
    fireEvent.click(saveButton());
    await screen.findByText(/didn't save/i);

    fireEvent.change(sizeSelect(), { target: { value: "5" } });

    expect(screen.queryByText(/didn't save/i)).not.toBeInTheDocument();
  });
});

// ─── Accessibility ───────────────────────────────────────────────────

describe("ProtocolSettings accessibility", () => {
  it("is a real disclosure button that reports its state", async () => {
    render(<ProtocolSettings />);

    const toggle = screen.getByRole("button", { name: TOGGLE });
    expect(toggle.tagName).toBe("BUTTON");
    expect(toggle).toHaveAttribute("type", "button");
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await screen.findByRole("combobox");
  });

  it("keeps the panel out of the tree while it is collapsed", async () => {
    render(<ProtocolSettings />);

    const toggle = screen.getByRole("button", { name: TOGGLE });
    const panel = document.getElementById(
      toggle.getAttribute("aria-controls") ?? "",
    );
    expect(panel).not.toBeNull();
    expect(panel).toHaveAttribute("hidden");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("leaves focus on the toggle when the panel opens", async () => {
    render(<ProtocolSettings />);

    const toggle = screen.getByRole("button", { name: TOGGLE });
    toggle.focus();
    fireEvent.click(toggle);

    await screen.findByRole("combobox");
    expect(toggle).toHaveFocus();
  });

  it("keeps the save button focusable after it goes inert", async () => {
    // aria-disabled rather than disabled: a save that lands should not
    // drop the keyboard user who just pressed it back to the top.
    mockUpdate.mockResolvedValue(settings({ protocol_size: 6 }));
    await openSettings();
    fireEvent.change(sizeSelect(), { target: { value: "6" } });

    const save = saveButton();
    save.focus();
    fireEvent.click(save);

    await waitFor(() => expect(save).toHaveAttribute("aria-disabled", "true"));
    expect(save).toHaveFocus();
  });

  it("names every group of controls", async () => {
    mockGet.mockResolvedValue(settings({ active_pack_ids: [FOUNDATIONS] }));
    await openSettings();

    const groups = screen.getAllByRole("group");
    expect(groups.length).toBeGreaterThanOrEqual(2);
    for (const group of groups) {
      expect(group.tagName).toBe("FIELDSET");
      expect(group).toHaveAccessibleName();
    }
  });

  it("ties the size control to a label and its helper line", async () => {
    await openSettings();

    const select = sizeSelect();
    expect(select).toHaveAccessibleName("Practices a day");
    expect(select).toHaveAccessibleDescription(/up to this many a day/i);
  });

  it("puts the save verdict in a live region", async () => {
    mockUpdate.mockResolvedValue(settings({ protocol_size: 6 }));
    await openSettings();

    const region = screen.getByRole("status");
    expect(region).toHaveAttribute("aria-live", "polite");

    fireEvent.change(sizeSelect(), { target: { value: "6" } });
    fireEvent.click(saveButton());

    await waitFor(() => expect(region).toHaveTextContent(/saved\./i));
  });

  it("gives every control a touch target and a focus ring", async () => {
    await openSettings();

    for (const control of [
      screen.getByRole("button", { name: TOGGLE }),
      sizeSelect(),
      saveButton(),
      screen.getByRole("radio", { name: ALL_PACKS }).closest("label")!,
    ]) {
      expect(control.className).toContain("touch-target");
    }
    for (const control of [
      screen.getByRole("button", { name: TOGGLE }),
      sizeSelect(),
      saveButton(),
      screen.getByRole("radio", { name: ALL_PACKS }),
    ]) {
      expect(control.className).toContain("focus-visible:ring-2");
      // /60 rather than the /50 used elsewhere in the app: it is the
      // computed value that clears the 3:1 floor WCAG 1.4.11 asks of a
      // focus indicator. Pinned so the ring cannot drift back down.
      expect(control.className).toContain("focus-visible:ring-primary/60");
    }
  });

  it("animates nothing", async () => {
    const { container } = await openSettings();

    expect(container.innerHTML).not.toContain("animate-");
    expect(container.innerHTML).not.toContain("transition-transform");
  });
});

// ─── Copy ────────────────────────────────────────────────────────────

describe("ProtocolSettings copy", () => {
  it("uses no em-dashes", async () => {
    const { container } = await openSettings();

    expect(container.textContent).not.toContain("—");
  });

  it("says the size is a ceiling rather than a promise", async () => {
    // Issue #326: a number in a box reads as a guarantee of that many
    // practices, and the recommender offers fewer when fewer are ready.
    await openSettings();

    expect(screen.getByText(/some days will offer fewer/i)).toBeInTheDocument();
  });
});
