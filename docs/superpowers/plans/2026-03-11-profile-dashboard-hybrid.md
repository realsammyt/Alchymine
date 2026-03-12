# Profile/Dashboard Hybrid Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a profile summary card to the dashboard and upgrade the profile page with visual restyling, section-level edit mode for intake fields, and improved navigation placement.

**Architecture:** New self-contained `ProfileSummaryCard` component on the dashboard (same pattern as `IntakeCTA`). Profile page gets `card-surface` + colored left border restyling, section-level edit mode using `saveIntake()`, and nav reordering. Frontend-only — no backend changes.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Next.js App Router, existing API client (`getProfile`, `saveIntake`), existing hooks (`useAuth`, `useIntake`, `useApi`)

---

## File Structure

| File                                                                 | Responsibility                                           | Action                     |
| -------------------------------------------------------------------- | -------------------------------------------------------- | -------------------------- |
| `alchymine/web/src/components/shared/ProfileSummaryCard.tsx`         | Dashboard identity card + system completion dots         | **Create**                 |
| `alchymine/web/src/__tests__/components/ProfileSummaryCard.test.tsx` | Tests for ProfileSummaryCard                             | **Create**                 |
| `alchymine/web/src/app/dashboard/page.tsx`                           | Import + render ProfileSummaryCard                       | **Modify** (2 lines)       |
| `alchymine/web/src/app/profile/page.tsx`                             | Restyle sections, add edit mode, restructure data export | **Modify** (major rewrite) |
| `alchymine/web/src/__tests__/components/ProfilePage.test.tsx`        | Tests for profile page edit mode                         | **Create**                 |
| `alchymine/web/src/components/shared/Navigation.tsx`                 | Reorder NAV_ITEMS, adjust mobile bottom bar              | **Modify** (~10 lines)     |

---

## Chunk 1: ProfileSummaryCard + Dashboard Integration

### Task 1: Create ProfileSummaryCard Component

**Files:**

- Create: `alchymine/web/src/components/shared/ProfileSummaryCard.tsx`
- Create: `alchymine/web/src/__tests__/components/ProfileSummaryCard.test.tsx`

**Context:** Follow the `IntakeCTA` pattern at `alchymine/web/src/components/shared/IntakeCTA.tsx` — self-contained, no props, fetches own data, returns null when not applicable. Use the color tokens from `SYSTEM_META` in `alchymine/web/src/components/spiral/SpiralHub.tsx` lines 92-155 for system dot colors.

- [ ] **Step 1: Write the test file**

```tsx
// alchymine/web/src/__tests__/components/ProfileSummaryCard.test.tsx
import { render, screen } from "@testing-library/react";
import ProfileSummaryCard from "@/components/shared/ProfileSummaryCard";

// Mock next/link
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

// Mock useAuth
jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "test-user", email: "test@example.com" },
    isLoading: false,
  }),
}));

// Mock useIntake
const mockUseIntake = jest.fn();
jest.mock("@/lib/useApi", () => ({
  useIntake: (...args: unknown[]) => mockUseIntake(...args),
  useApi: jest
    .fn()
    .mockReturnValue({ data: null, loading: false, error: null }),
}));

// Mock getProfile
jest.mock("@/lib/api", () => ({
  getProfile: jest.fn(),
}));

describe("ProfileSummaryCard", () => {
  it("returns null when intake is loading", () => {
    mockUseIntake.mockReturnValue({ data: null, loading: true });
    const { container } = render(<ProfileSummaryCard />);
    expect(container.firstChild).toBeNull();
  });

  it("returns null when no intake data exists", () => {
    mockUseIntake.mockReturnValue({ data: null, loading: false });
    const { container } = render(<ProfileSummaryCard />);
    expect(container.firstChild).toBeNull();
  });

  it("renders user name when intake data exists", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    expect(screen.getByText("Sam Thompson")).toBeInTheDocument();
  });

  it("renders View Full Profile link", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    const link = screen.getByText("View Full Profile");
    expect(link.closest("a")).toHaveAttribute("href", "/profile");
  });

  it("renders 5 system dots", () => {
    mockUseIntake.mockReturnValue({
      data: { fullName: "Sam Thompson", birthDate: "1990-03-15" },
      loading: false,
    });
    render(<ProfileSummaryCard />);
    const dots = screen.getAllByTestId(/^system-dot-/);
    expect(dots).toHaveLength(5);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd alchymine/web && npx jest --testPathPattern ProfileSummaryCard --no-coverage`
Expected: FAIL — module not found

- [ ] **Step 3: Implement ProfileSummaryCard**

```tsx
// alchymine/web/src/components/shared/ProfileSummaryCard.tsx
"use client";

import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { useIntake, useApi } from "@/lib/useApi";
import { getProfile, ProfileResponse } from "@/lib/api";

const SYSTEMS = [
  { key: "identity", label: "I", name: "Intelligence", color: "#DAA520" },
  { key: "healing", label: "H", name: "Healing", color: "#20B2AA" },
  { key: "wealth", label: "W", name: "Wealth", color: "#DAA520" },
  { key: "creative", label: "C", name: "Creative", color: "#9B4DCA" },
  { key: "perspective", label: "P", name: "Perspective", color: "#7B2D8E" },
] as const;

export default function ProfileSummaryCard() {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const { data: intake, loading: intakeLoading } = useIntake(userId);

  const profile = useApi<ProfileResponse>(
    () => (userId ? getProfile(userId) : Promise.reject(new Error("No user"))),
    [userId],
  );

  // Don't render while loading or if no intake
  if (intakeLoading || !intake?.fullName) return null;

  const identityData = profile.data?.identity;
  const lifePath = identityData?.life_path as number | undefined;
  const sunSign = identityData?.sun_sign as string | undefined;
  const archetype = identityData?.primary_archetype as string | undefined;

  return (
    <div className="card-surface border border-white/[0.06] rounded-2xl px-5 py-4 sm:px-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Identity badge */}
        <div className="flex items-center gap-4 sm:items-start">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 text-2xl">
            {archetype ? "🔮" : "✨"}
          </div>
          <div className="min-w-0">
            <h3 className="font-display text-lg font-light text-text truncate">
              {intake.fullName}
            </h3>
            <p className="font-body text-xs text-text/40 mt-0.5">
              {[
                lifePath != null ? `Life Path ${lifePath}` : null,
                sunSign ? `${sunSign} ☉` : null,
              ]
                .filter(Boolean)
                .join(" · ") || "Generating your profile…"}
            </p>
            {archetype && (
              <p className="font-body text-xs text-primary/70 mt-0.5">
                {archetype}
              </p>
            )}
          </div>
        </div>

        {/* System completion dots + link */}
        <div className="flex flex-col items-center sm:items-end gap-2">
          <div className="flex items-center gap-2">
            {SYSTEMS.map(({ key, label, name, color }) => {
              const filled = profile.data
                ? profile.data[key as keyof ProfileResponse] !== null
                : false;
              return (
                <div
                  key={key}
                  data-testid={`system-dot-${key}`}
                  title={`${name}: ${filled ? "Active" : "Not started"}`}
                  className="flex flex-col items-center gap-1"
                >
                  <div
                    className="w-3 h-3 rounded-full transition-all duration-300"
                    style={{
                      background: filled ? color : "rgba(255,255,255,0.06)",
                      border: filled
                        ? `1.5px solid ${color}`
                        : "1.5px solid rgba(255,255,255,0.1)",
                      boxShadow: filled ? `0 0 8px ${color}44` : "none",
                    }}
                  />
                  <span className="text-[9px] font-body text-text/25">
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
          <Link
            href="/profile"
            className="font-body text-xs text-primary/60 hover:text-primary transition-colors no-underline"
          >
            View Full Profile →
          </Link>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd alchymine/web && npx jest --testPathPattern ProfileSummaryCard --no-coverage`
Expected: 5 passing tests

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/components/shared/ProfileSummaryCard.tsx alchymine/web/src/__tests__/components/ProfileSummaryCard.test.tsx
git commit -m "feat: add ProfileSummaryCard component with tests"
```

---

### Task 2: Integrate ProfileSummaryCard into Dashboard

**Files:**

- Modify: `alchymine/web/src/app/dashboard/page.tsx` (2 lines: import + JSX)

**Context:** The dashboard overview tab starts at line 808. The first child inside the `space-y-6` div is a `MotionReveal` wrapping the "Overall Progress" card at line 810. Insert the `ProfileSummaryCard` before it.

- [ ] **Step 1: Add import at top of dashboard/page.tsx**

After the existing imports (around line 9), add:

```tsx
import ProfileSummaryCard from "@/components/shared/ProfileSummaryCard";
```

- [ ] **Step 2: Add component inside the overview tab**

At line 814 (inside the `<div className="space-y-6">` for the overview tab), add before the first `<MotionReveal>`:

```tsx
<ProfileSummaryCard />
```

- [ ] **Step 3: Run existing dashboard tests to verify nothing breaks**

Run: `cd alchymine/web && npx jest --testPathPattern DashboardPage --no-coverage`
Expected: All existing tests pass (may need to add a mock for ProfileSummaryCard)

If tests fail because ProfileSummaryCard introduces new dependencies, add this mock to the test file:

```tsx
jest.mock("@/components/shared/ProfileSummaryCard", () => {
  return function MockProfileSummaryCard() {
    return null;
  };
});
```

- [ ] **Step 4: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/app/dashboard/page.tsx alchymine/web/src/__tests__/components/DashboardPage.test.tsx
git commit -m "feat: add ProfileSummaryCard to dashboard overview tab"
```

---

## Chunk 2: Navigation Reordering

### Task 3: Reorder NAV_ITEMS and Update Mobile Bottom Bar

**Files:**

- Modify: `alchymine/web/src/components/shared/Navigation.tsx:17-78` (NAV_ITEMS array)
- Modify: `alchymine/web/src/components/shared/Navigation.tsx:361` (mobile bottom bar slice)
- Modify: `alchymine/web/src/components/shared/Navigation.tsx:377-388` (mobile bottom bar short labels)

**Context:** The `NAV_ITEMS` array at line 17 has Profile at index 8 (9th). Move it to index 2 (3rd). The mobile bottom bar at line 361 uses `NAV_ITEMS.slice(0, 6)` — with Profile at index 2, the slice naturally includes it and drops Perspective (which was at index 6 before, now at index 7).

- [ ] **Step 1: Move Profile entry from index 8 to index 2**

In `Navigation.tsx`, move the Profile entry (currently lines 66-71) to after the Discover entry (after line 29):

```tsx
const NAV_ITEMS: NavItem[] = [
  {
    name: "Dashboard",
    href: "/dashboard",
    icon: "home",
    label: "Dashboard overview",
  },
  {
    name: "Discover",
    href: "/discover",
    icon: "spiral",
    label: "Intake and assessment flow",
  },
  {
    name: "Profile",
    href: "/profile",
    icon: "user",
    label: "Your unified profile",
  }, // MOVED
  {
    name: "Intelligence",
    href: "/intelligence",
    icon: "brain",
    label: "Personalized Intelligence system",
  },
  {
    name: "Healing",
    href: "/healing",
    icon: "leaf",
    label: "Ethical Healing system",
  },
  {
    name: "Wealth",
    href: "/wealth",
    icon: "chart",
    label: "Generational Wealth system",
  },
  {
    name: "Creative",
    href: "/creative",
    icon: "palette",
    label: "Creative Development system",
  },
  {
    name: "Perspective",
    href: "/perspective",
    icon: "telescope",
    label: "Perspective Enhancement system",
  },
  {
    name: "Journal",
    href: "/journal",
    icon: "book",
    label: "Reflection journal",
  },
  { name: "About", href: "/about", icon: "info", label: "About Alchymine" },
];
```

- [ ] **Step 2: Add "Profile" short label to mobile bottom bar mapping**

At line 377-388 (the mobile bottom bar short label mapping), add Profile:

```tsx
{
  Dashboard: "Home",
  Discover: "Discover",
  Profile: "Profile",     // ADD
  Intelligence: "Mind",
  Healing: "Heal",
  Wealth: "Wealth",
  Creative: "Create",
  Perspective: "View",
}
```

Note: `NAV_ITEMS.slice(0, 6)` now yields: Dashboard, Discover, Profile, Intelligence, Healing, Wealth — which is exactly the desired mobile bottom bar.

- [ ] **Step 3: Run Navigation tests**

Run: `cd alchymine/web && npx jest --testPathPattern Navigation --no-coverage`
Expected: All pass (test may need updating if it checks nav order)

- [ ] **Step 4: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/components/shared/Navigation.tsx
git commit -m "feat: move Profile to 3rd nav position, add to mobile bottom bar"
```

---

## Chunk 3: Profile Page Restyling + Edit Mode

### Task 4: Restyle Profile Sections with Colored Left Borders

**Files:**

- Modify: `alchymine/web/src/app/profile/page.tsx:30-61` (ProfileSection component)

**Context:** Currently `ProfileSection` uses `card-surface border ${accentBorder} p-6`. Change to use `border-l-4` pattern (matching dashboard's SystemCard). Each section gets a colored left border instead of a full border.

- [ ] **Step 1: Update ProfileSection styling**

Replace the `ProfileSection` component (lines 30-61) with:

```tsx
function ProfileSection({
  title,
  accentText,
  accentBg,
  accentColor,
  icon,
  editButton,
  children,
}: {
  title: string;
  accentText: string;
  accentBg: string;
  accentColor: string;
  icon: React.ReactNode;
  editButton?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div
      className="card-surface border-l-4 px-5 py-5 sm:px-6"
      style={{ borderLeftColor: accentColor }}
    >
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-xl ${accentBg} flex items-center justify-center flex-shrink-0`}
            aria-hidden="true"
          >
            {icon}
          </div>
          <h2 className={`font-display text-xl font-light ${accentText}`}>
            {title}
          </h2>
        </div>
        {editButton}
      </div>
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Update all section components to pass `accentColor`**

Each section caller needs to add the `accentColor` prop. The colors match `SYSTEM_META`:

- `IdentitySection`: `accentColor="#DAA520"`
- `HealingSection`: `accentColor="#20B2AA"`
- `WealthSection`: `accentColor="#DAA520"`
- `CreativeSection`: `accentColor="#9B4DCA"`
- `PerspectiveSection`: `accentColor="#7B2D8E"`

Also remove the `accentBorder` prop from each caller since the left border now uses inline `style`.

- [ ] **Step 3: Add "Explore {System}" footer links to each section**

After the children content in each section, add a footer link. Example for IdentitySection:

```tsx
{
  /* Footer */
}
<div className="mt-4 pt-3 border-t border-white/[0.04]">
  <Link
    href="/intelligence"
    className="font-body text-xs text-primary/60 hover:text-primary transition-colors no-underline"
  >
    Explore Intelligence →
  </Link>
</div>;
```

Repeat for each section with appropriate href and accent color.

- [ ] **Step 4: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add alchymine/web/src/app/profile/page.tsx
git commit -m "feat: restyle profile sections with colored left borders and system links"
```

---

### Task 5: Add Section-Level Edit Mode for Intelligence and Wealth

**Files:**

- Modify: `alchymine/web/src/app/profile/page.tsx` (IdentitySection, WealthSection)
- Create: `alchymine/web/src/__tests__/components/ProfilePage.test.tsx`

**Context:** Only Intelligence (intake fields: full_name, birth_date, birth_time, birth_city, intentions) and Wealth (financial context fields) have editable intake data. Healing, Creative, and Perspective are fully computed — no edit button.

The edit mode uses `saveIntake()` from `alchymine/web/src/lib/api.ts:897-915`. The save function takes `userId` and a data object with all intake fields.

- [ ] **Step 1: Write tests for edit mode**

```tsx
// alchymine/web/src/__tests__/components/ProfilePage.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import ProfilePage from "@/app/profile/page";

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) {
    return <a href={href}>{children}</a>;
  };
});

jest.mock("next/navigation", () => ({
  useRouter: jest.fn().mockReturnValue({ push: jest.fn(), replace: jest.fn() }),
  usePathname: jest.fn().mockReturnValue("/profile"),
}));

jest.mock("@/lib/AuthContext", () => ({
  useAuth: jest.fn().mockReturnValue({
    user: { id: "test-user", email: "test@example.com" },
    isLoading: false,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  }),
}));

const mockProfile = {
  id: "profile-1",
  version: "2.0",
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  intake: {
    full_name: "Sam Thompson",
    birth_date: "1990-03-15",
    birth_time: "14:30",
    birth_city: "New York",
    intention: "career",
    intentions: ["career", "purpose"],
  },
  identity: {
    life_path: 7,
    sun_sign: "Pisces",
    primary_archetype: "The Alchemist",
  },
  healing: null,
  wealth: null,
  creative: null,
  perspective: null,
};

jest.mock("@/lib/useApi", () => ({
  useApi: jest
    .fn()
    .mockReturnValue({ data: mockProfile, loading: false, error: null }),
  useIntake: jest
    .fn()
    .mockReturnValue({ data: { fullName: "Sam Thompson" }, loading: false }),
}));

jest.mock("@/lib/api", () => ({
  getProfile: jest.fn(),
  saveIntake: jest.fn().mockResolvedValue({}),
}));

jest.mock("@/components/shared/ProtectedRoute", () => {
  return function MockProtectedRoute({
    children,
  }: {
    children: React.ReactNode;
  }) {
    return <>{children}</>;
  };
});

describe("ProfilePage", () => {
  it("renders profile header", () => {
    render(<ProfilePage />);
    expect(screen.getByText(/Profile/)).toBeInTheDocument();
  });

  it("shows Edit button for Intelligence section", () => {
    render(<ProfilePage />);
    const editButtons = screen.getAllByText("Edit");
    expect(editButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("toggles edit mode when Edit is clicked", () => {
    render(<ProfilePage />);
    const editButton = screen.getAllByText("Edit")[0];
    fireEvent.click(editButton);
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
  });

  it("shows Explore links for each section", () => {
    render(<ProfilePage />);
    expect(screen.getByText(/Explore Intelligence/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd alchymine/web && npx jest --testPathPattern ProfilePage --no-coverage`
Expected: FAIL

- [ ] **Step 3: Add edit state management to ProfilePage**

At the top of `ProfilePage` component (line 506), add state:

```tsx
const [editingSection, setEditingSection] = useState<string | null>(null);
const [editForm, setEditForm] = useState<Record<string, unknown>>({});
const [saving, setSaving] = useState(false);
const [saveSuccess, setSaveSuccess] = useState(false);
```

Add imports:

```tsx
import { useState } from "react";
import { getProfile, ProfileResponse, saveIntake } from "@/lib/api";
```

Add save handler:

```tsx
const handleSave = async () => {
  if (!userId || !profileState.data?.intake) return;
  setSaving(true);
  try {
    const currentIntake = profileState.data.intake;
    await saveIntake(userId, {
      full_name: (editForm.full_name as string) ?? currentIntake.full_name,
      birth_date: (editForm.birth_date as string) ?? currentIntake.birth_date,
      birth_time:
        (editForm.birth_time as string) ??
        currentIntake.birth_time ??
        undefined,
      birth_city:
        (editForm.birth_city as string) ??
        currentIntake.birth_city ??
        undefined,
      intention: currentIntake.intention,
      intentions: currentIntake.intentions,
      wealth_context:
        (editForm.wealth_context as IntakePayload["wealth_context"]) ??
        undefined,
    });
    setSaveSuccess(true);
    setEditingSection(null);
    setEditForm({});
    // Trigger refetch by updating deps
    profileState.refetch?.();
    setTimeout(() => setSaveSuccess(false), 3000);
  } catch {
    // Error handled inline
  } finally {
    setSaving(false);
  }
};

const startEdit = (section: string, initialData: Record<string, unknown>) => {
  setEditingSection(section);
  setEditForm(initialData);
  setSaveSuccess(false);
};

const cancelEdit = () => {
  setEditingSection(null);
  setEditForm({});
};
```

- [ ] **Step 4: Update IdentitySection to support edit mode**

Pass edit props to IdentitySection:

```tsx
<IdentitySection
  profile={profileState.data}
  editing={editingSection === "intelligence"}
  editForm={editForm}
  onEditForm={setEditForm}
  onStartEdit={() =>
    startEdit("intelligence", {
      full_name: profileState.data!.intake!.full_name,
      birth_date: profileState.data!.intake!.birth_date,
      birth_time: profileState.data!.intake!.birth_time ?? "",
      birth_city: profileState.data!.intake!.birth_city ?? "",
    })
  }
  onSave={handleSave}
  onCancel={cancelEdit}
  saving={saving}
/>
```

In `IdentitySection`, add an Edit button in the header and toggle between view/edit:

```tsx
function IdentitySection({
  profile,
  editing,
  editForm,
  onEditForm,
  onStartEdit,
  onSave,
  onCancel,
  saving,
}: {
  profile: ProfileResponse;
  editing: boolean;
  editForm: Record<string, unknown>;
  onEditForm: (form: Record<string, unknown>) => void;
  onStartEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
```

When `editing` is true, render inputs instead of `FieldRow` for intake fields (full_name, birth_date, birth_time, birth_city). Computed fields (life_path, sun_sign, etc.) stay as read-only `FieldRow` with a `(computed)` suffix.

Input styling matches the intake form: `bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm font-body text-text focus:outline-none focus:border-primary/40`

Show Save/Cancel buttons at the bottom of the section:

```tsx
{
  editing && (
    <div className="flex items-center gap-3 mt-4 pt-3 border-t border-white/[0.04]">
      <button
        onClick={onSave}
        disabled={saving}
        className="px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-40"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        onClick={onCancel}
        className="px-4 py-2 text-sm text-text/40 hover:text-text/60 transition-colors"
      >
        Cancel
      </button>
      <p className="font-body text-[0.65rem] text-text/25 ml-auto">
        Computed fields update on next report generation.
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Apply the same edit mode pattern to WealthSection**

WealthSection editable fields: income_range, has_investments, has_business, has_real_estate, dependents, debt_level, financial_goal. Use select elements for income_range and debt_level (reuse the `INCOME_RANGES` and `DEBT_LEVELS` constants from `discover/intake/page.tsx`), checkboxes for booleans, number input for dependents.

- [ ] **Step 6: Run all tests**

Run: `cd alchymine/web && npx jest --no-coverage`
Expected: All pass

- [ ] **Step 7: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 8: Commit**

```bash
git add alchymine/web/src/app/profile/page.tsx alchymine/web/src/__tests__/components/ProfilePage.test.tsx
git commit -m "feat: add section-level edit mode for Intelligence and Wealth on profile page"
```

---

### Task 6: Restructure Data Export Section

**Files:**

- Modify: `alchymine/web/src/app/profile/page.tsx:535-562` (download button in header)

**Context:** Move the download button from the header to a dedicated "Your Data" card section at the bottom of the profile page, after the five system sections.

- [ ] **Step 1: Remove the download button from the header**

Remove the `{profileState.data && (<button...>)}` block from lines 535-562.

- [ ] **Step 2: Add a "Your Data" section after the five system sections**

After the `PerspectiveSection` MotionStaggerItem (line 603), add:

```tsx
<MotionStaggerItem>
  <div className="card-surface px-5 py-5 sm:px-6">
    <h2 className="font-display text-lg font-light text-text mb-2">
      Your Data
    </h2>
    <p className="font-body text-xs text-text/40 mb-4">
      Your data belongs to you. Download a complete copy of everything Alchymine
      knows about you.
    </p>
    <button
      onClick={() =>
        downloadProfileJson(profileState.data!, user?.email ?? "user")
      }
      className="inline-flex items-center gap-2 px-4 py-2 bg-white/[0.04] border border-white/10 text-text/60 font-body text-sm rounded-lg hover:bg-white/[0.08] hover:text-text transition-colors"
    >
      <svg
        className="w-4 h-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      Download JSON
    </button>
  </div>
</MotionStaggerItem>
```

- [ ] **Step 3: Run TypeScript check**

Run: `cd alchymine/web && npx tsc --noEmit`
Expected: Clean

- [ ] **Step 4: Commit**

```bash
git add alchymine/web/src/app/profile/page.tsx
git commit -m "feat: move data export to dedicated section at bottom of profile page"
```

---

## Verification

- [ ] Run full test suite: `cd alchymine/web && npm test`
- [ ] Run type check: `cd alchymine/web && npx tsc --noEmit`
- [ ] Manual: open /dashboard — ProfileSummaryCard appears above Overall Score
- [ ] Manual: open /profile — sections have colored left borders, Edit buttons on Intelligence/Wealth
- [ ] Manual: click Edit on Intelligence — fields become inputs, Save/Cancel appear
- [ ] Manual: save an edit — profile refreshes with updated data
- [ ] Manual: check mobile — Profile appears in bottom nav bar
- [ ] Manual: check mobile — ProfileSummaryCard stacks vertically
