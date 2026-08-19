import { act, fireEvent, render, screen } from "@testing-library/react";
import PracticePage from "../page";
import {
  getEcologySettings,
  getPracticeSummary,
  getPracticeToday,
  listPracticeLog,
  listPracticePacks,
  listPractices,
} from "@/lib/api";
import { localDayKey } from "@/lib/localDay";

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) {
    return (
      <a href={href} {...props}>
        {children}
      </a>
    );
  };
});

jest.mock("next/navigation", () => ({
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "user-1", email: "test@example.com" },
    isLoading: false,
    login: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock("@/lib/api", () => {
  const actual = jest.requireActual("@/lib/api");
  return {
    ...actual,
    getPracticeToday: jest.fn(),
    getPracticeSummary: jest.fn(),
    listPractices: jest.fn(),
    listPracticeLog: jest.fn(),
    getEcologySettings: jest.fn(),
    listPracticePacks: jest.fn(),
  };
});

const mockToday = getPracticeToday as jest.Mock;
const mockSummary = getPracticeSummary as jest.Mock;
const mockLibrary = listPractices as jest.Mock;
const mockLog = listPracticeLog as jest.Mock;
const mockEcology = getEcologySettings as jest.Mock;
const mockPacks = listPracticePacks as jest.Mock;

const TOGGLE = /protocol settings/i;

/** Let every settled promise in the page's chain land. */
async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

beforeEach(() => {
  for (const mock of [
    mockToday,
    mockSummary,
    mockLibrary,
    mockLog,
    mockEcology,
    mockPacks,
  ]) {
    mock.mockReset();
  }
  mockToday.mockResolvedValue({
    day_key: localDayKey(),
    generated_at: "2026-08-19T08:00:00+00:00",
    protocol_size: 3,
    items: [],
    slots: {},
  });
  mockSummary.mockResolvedValue({
    day_key: localDayKey(),
    days_practiced_last_7: 0,
    last_7: [false, false, false, false, false, false, false],
    by_purpose: {},
    total_completed: 0,
  });
  mockLibrary.mockResolvedValue([]);
  mockLog.mockResolvedValue({ entries: [], total: 0, page: 1, per_page: 100 });
  mockEcology.mockResolvedValue({ protocol_size: 3, active_pack_ids: null });
  mockPacks.mockResolvedValue([]);
});

describe("practice page settings block", () => {
  it("offers the settings collapsed, with the practices still the page", async () => {
    render(<PracticePage />);
    await flush();

    const toggle = await screen.findByRole("button", { name: TOGGLE });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    // Collapsed means collapsed: nothing inside the panel is reachable,
    // and the settings have cost the page no requests yet.
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(mockEcology).not.toHaveBeenCalled();
  });

  it("opens the settings on the page it belongs to", async () => {
    render(<PracticePage />);
    await flush();

    fireEvent.click(screen.getByRole("button", { name: TOGGLE }));

    expect(
      await screen.findByRole("combobox", { name: /practices a day/i }),
    ).toHaveValue("3");
    expect(screen.getByRole("button", { name: /save settings/i })).toBeInTheDocument();
  });

  it("keeps the practice heading above the settings", async () => {
    render(<PracticePage />);
    await flush();

    const headings = screen.getAllByRole("heading");
    expect(headings[0]).toHaveTextContent(/today's practice/i);
    expect(headings[0].tagName).toBe("H1");
  });
});
