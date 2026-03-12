"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useAuth } from "@/lib/AuthContext";
import { useApi } from "@/lib/useApi";
import {
  getProfile,
  getCompleteness,
  saveIntake,
  listUserReports,
  ProfileResponse,
  IntakePayload,
  type CompletenessResponse,
  type ReportListResponse,
} from "@/lib/api";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

// ── Spinner ───────────────────────────────────────────────────────

function Spinner() {
  return (
    <div
      className="flex justify-center py-12"
      role="status"
      aria-label="Loading"
    >
      <div className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────

function ProfileSection({
  title,
  accentText,
  accentBg,
  accentColor,
  icon,
  editButton,
  footerHref,
  footerLabel,
  children,
}: {
  title: string;
  accentText: string;
  accentBg: string;
  accentColor: string;
  icon: React.ReactNode;
  editButton?: React.ReactNode;
  footerHref: string;
  footerLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="card-surface border-l-4 p-6"
      style={{ borderColor: accentColor }}
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
      <div className="mt-5 pt-4 border-t border-white/[0.05]">
        <Link
          href={footerHref}
          className={`font-body text-sm ${accentText} hover:underline underline-offset-2 transition-colors`}
        >
          {footerLabel} &rarr;
        </Link>
      </div>
    </div>
  );
}

// ── Field row ─────────────────────────────────────────────────────

function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-white/[0.05] last:border-0">
      <span className="font-body text-xs text-text/40 uppercase tracking-wide flex-shrink-0">
        {label}
      </span>
      <span className="font-body text-sm text-text/80 text-right">
        {String(value)}
      </span>
    </div>
  );
}

// ── Tag list ──────────────────────────────────────────────────────

function TagList({
  items,
  accentBg,
  accentText,
}: {
  items: string[];
  accentBg: string;
  accentText: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className={`px-3 py-1 ${accentBg} ${accentText} font-body text-xs rounded-full`}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

// ── Empty layer placeholder ───────────────────────────────────────

function EmptyLayer({
  href,
  accentText,
  linkText,
}: {
  href: string;
  accentText: string;
  linkText: string;
}) {
  return (
    <p className="font-body text-sm text-text/40">
      No data yet.{" "}
      <Link
        href={href}
        className={`${accentText} underline underline-offset-2`}
      >
        {linkText}
      </Link>
    </p>
  );
}

// ── Edit form types ──────────────────────────────────────────────

interface IdentityEditForm {
  full_name: string;
  birth_date: string;
  birth_time: string;
  birth_city: string;
}

interface WealthEditForm {
  income_range: string;
  has_investments: boolean | null;
  has_business: boolean | null;
  has_real_estate: boolean | null;
  dependents: number | null;
  debt_level: string;
  financial_goal: string;
}

type EditingSection = "identity" | "wealth" | null;

// ── Edit helper components ──────────────────────────────────────

const editInputClass =
  "bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm font-body text-text focus:outline-none focus:border-primary/40 w-full";

function EditField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-white/[0.05] last:border-0">
      <span className="font-body text-xs text-text/40 uppercase tracking-wide flex-shrink-0 pt-2">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${editInputClass} max-w-[220px]`}
      />
    </div>
  );
}

function EditSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-white/[0.05] last:border-0">
      <span className="font-body text-xs text-text/40 uppercase tracking-wide flex-shrink-0 pt-2">
        {label}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`${editInputClass} max-w-[220px] [&>option]:bg-[#141420] [&>option]:text-text`}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function EditToggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-white/[0.05] last:border-0">
      <span className="font-body text-xs text-text/40 uppercase tracking-wide flex-shrink-0">
        {label}
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={!!value}
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          value ? "bg-primary/60" : "bg-white/10"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
            value ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

function ComputedField({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex items-start justify-between gap-4 py-2 border-b border-white/[0.05] last:border-0">
      <span className="font-body text-xs text-text/40 uppercase tracking-wide flex-shrink-0">
        {label}
      </span>
      <div className="text-right">
        <span className="font-body text-sm text-text/80">
          {String(value)}
        </span>
        <span className="font-body text-[10px] text-text/25 ml-2">
          (computed)
        </span>
      </div>
    </div>
  );
}

function EditActions({
  onSave,
  onCancel,
  saving,
}: {
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
}) {
  return (
    <div className="flex items-center gap-3 pt-3">
      <button
        onClick={onSave}
        disabled={saving}
        className="px-4 py-2 bg-primary/20 border border-primary/30 text-primary font-body text-sm rounded-lg hover:bg-primary/30 transition-colors disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save"}
      </button>
      <button
        onClick={onCancel}
        disabled={saving}
        className="px-4 py-2 bg-white/[0.04] border border-white/10 text-text/60 font-body text-sm rounded-lg hover:bg-white/[0.08] transition-colors disabled:opacity-50"
      >
        Cancel
      </button>
    </div>
  );
}

// ── Identity Section ──────────────────────────────────────────────

function IdentitySection({
  profile,
  editing,
  onEdit,
  onCancel,
  onSave,
  editForm,
  setEditForm,
  saving,
}: {
  profile: ProfileResponse;
  editing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  editForm: IdentityEditForm;
  setEditForm: (form: IdentityEditForm) => void;
  saving: boolean;
}) {
  const identity = profile.identity;
  const intake = profile.intake;

  const hasData = !!(identity || intake);

  return (
    <ProfileSection
      title="Personal Intelligence"
      accentText="text-primary"
      accentBg="bg-primary/10"
      accentColor="#DAA520"
      footerHref="/intelligence"
      footerLabel="Explore Intelligence"
      icon={
        <svg
          className="w-5 h-5 text-primary"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      }
      editButton={
        hasData && !editing ? (
          <button
            onClick={onEdit}
            className="font-body text-xs text-text/40 hover:text-text/60 transition-colors"
          >
            Edit
          </button>
        ) : undefined
      }
    >
      {!hasData ? (
        <EmptyLayer
          href="/intelligence"
          accentText="text-primary"
          linkText="Explore Personal Intelligence"
        />
      ) : editing ? (
        <div className="space-y-3">
          <EditField
            label="Name"
            value={editForm.full_name}
            onChange={(v) => setEditForm({ ...editForm, full_name: v })}
          />
          <EditField
            label="Birth Date"
            value={editForm.birth_date}
            onChange={(v) => setEditForm({ ...editForm, birth_date: v })}
            type="date"
          />
          <EditField
            label="Birth Time"
            value={editForm.birth_time}
            onChange={(v) => setEditForm({ ...editForm, birth_time: v })}
            type="time"
          />
          <EditField
            label="Birth City"
            value={editForm.birth_city}
            onChange={(v) => setEditForm({ ...editForm, birth_city: v })}
          />
          {identity && (
            <>
              <ComputedField
                label="Life Path"
                value={(identity.numerology as Record<string, unknown>)?.life_path as number}
              />
              <ComputedField
                label="Expression"
                value={(identity.numerology as Record<string, unknown>)?.expression as number}
              />
              <ComputedField
                label="Soul Urge"
                value={(identity.numerology as Record<string, unknown>)?.soul_urge as number}
              />
              <ComputedField
                label="Sun Sign"
                value={(identity.astrology as Record<string, unknown>)?.sun_sign as string}
              />
              <ComputedField
                label="Moon Sign"
                value={(identity.astrology as Record<string, unknown>)?.moon_sign as string}
              />
              <ComputedField
                label="Rising Sign"
                value={(identity.astrology as Record<string, unknown>)?.rising_sign as string}
              />
              <ComputedField
                label="Archetype"
                value={(identity.archetype as Record<string, unknown>)?.primary as string}
              />
            </>
          )}
          <EditActions onSave={onSave} onCancel={onCancel} saving={saving} />
        </div>
      ) : (() => {
        const num = identity?.numerology as Record<string, unknown> | undefined;
        const ast = identity?.astrology as Record<string, unknown> | undefined;
        const arch = identity?.archetype as Record<string, unknown> | undefined;
        const pers = identity?.personality as Record<string, unknown> | undefined;
        return (
          <div className="space-y-1">
            {intake && (
              <>
                <FieldRow label="Name" value={intake.full_name} />
                <FieldRow label="Birth Date" value={intake.birth_date} />
                <FieldRow label="Birth Time" value={intake.birth_time} />
                <FieldRow label="Birth City" value={intake.birth_city} />
              </>
            )}
            <FieldRow label="Life Path" value={num?.life_path as number} />
            <FieldRow label="Expression" value={num?.expression as number} />
            <FieldRow label="Soul Urge" value={num?.soul_urge as number} />
            <FieldRow label="Sun Sign" value={ast?.sun_sign as string} />
            <FieldRow label="Moon Sign" value={ast?.moon_sign as string} />
            <FieldRow label="Rising Sign" value={ast?.rising_sign as string} />
            <FieldRow label="Archetype" value={arch?.primary as string} />
            <FieldRow label="Attachment Style" value={pers?.attachment_style as string} />
          </div>
        );
      })()}
    </ProfileSection>
  );
}

// ── Healing Section ───────────────────────────────────────────────

function HealingSection({ profile }: { profile: ProfileResponse }) {
  const healing = profile.healing;

  return (
    <ProfileSection
      title="Ethical Healing"
      accentText="text-accent"
      accentBg="bg-accent/10"
      accentColor="#20B2AA"
      footerHref="/healing"
      footerLabel="Explore Healing"
      icon={
        <svg
          className="w-5 h-5 text-accent"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M11 20A7 7 0 0 1 9.8 6.9C15.5 4.9 17 3.5 19 2c1 2 2 4.5 2 8 0 5.5-4.78 10-10 10Z" />
          <path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12" />
        </svg>
      }
    >
      {!healing ? (
        <EmptyLayer
          href="/healing"
          accentText="text-accent"
          linkText="Start Healing Journey"
        />
      ) : (() => {
        const mods = (healing.selected_modalities ?? healing.recommended_modalities) as Array<Record<string, unknown>> | undefined;
        const topMods = mods?.slice(0, 3).map((m) => (m.name ?? m.modality) as string).filter(Boolean);
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <FieldRow
                label="Crisis Protocol"
                value={healing.crisis_flag === true ? "Active" : healing.crisis_flag === false ? "Inactive" : undefined}
              />
              <FieldRow
                label="Openness"
                value={typeof healing.openness === "number" ? `${Math.round(healing.openness as number)}%` : undefined}
              />
              <FieldRow
                label="Attachment Style"
                value={healing.attachment_style as string}
              />
            </div>
            {topMods && topMods.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Recommended Modalities
                </p>
                <TagList
                  items={topMods}
                  accentBg="bg-accent/10"
                  accentText="text-accent"
                />
              </div>
            )}
          </div>
        );
      })()}
    </ProfileSection>
  );
}

// ── Wealth Section ────────────────────────────────────────────────

const INCOME_RANGES = [
  { value: "", label: "Select..." },
  { value: "under_30k", label: "Under $30k" },
  { value: "30k_50k", label: "$30k - $50k" },
  { value: "50k_75k", label: "$50k - $75k" },
  { value: "75k_100k", label: "$75k - $100k" },
  { value: "100k_150k", label: "$100k - $150k" },
  { value: "150k_250k", label: "$150k - $250k" },
  { value: "over_250k", label: "Over $250k" },
];

const DEBT_LEVELS = [
  { value: "", label: "Select..." },
  { value: "none", label: "None" },
  { value: "low", label: "Low" },
  { value: "moderate", label: "Moderate" },
  { value: "high", label: "High" },
  { value: "severe", label: "Severe" },
];

function WealthSection({
  profile,
  editing,
  onEdit,
  onCancel,
  onSave,
  editForm,
  setEditForm,
  saving,
}: {
  profile: ProfileResponse;
  editing: boolean;
  onEdit: () => void;
  onCancel: () => void;
  onSave: () => void;
  editForm: WealthEditForm;
  setEditForm: (form: WealthEditForm) => void;
  saving: boolean;
}) {
  const wealth = profile.wealth;
  const hasData = !!(wealth || profile.intake);

  return (
    <ProfileSection
      title="Generational Wealth"
      accentText="text-primary"
      accentBg="bg-primary/10"
      accentColor="#DAA520"
      footerHref="/wealth"
      footerLabel="Explore Wealth"
      icon={
        <svg
          className="w-5 h-5 text-primary"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="12" y1="20" x2="12" y2="10" />
          <line x1="18" y1="20" x2="18" y2="4" />
          <line x1="6" y1="20" x2="6" y2="16" />
        </svg>
      }
      editButton={
        hasData && !editing ? (
          <button
            onClick={onEdit}
            className="font-body text-xs text-text/40 hover:text-text/60 transition-colors"
          >
            Edit
          </button>
        ) : undefined
      }
    >
      {editing ? (
        <div className="space-y-3">
          <EditSelect
            label="Income Range"
            value={editForm.income_range}
            options={INCOME_RANGES}
            onChange={(v) => setEditForm({ ...editForm, income_range: v })}
          />
          <EditToggle
            label="Has Investments"
            value={editForm.has_investments}
            onChange={(v) => setEditForm({ ...editForm, has_investments: v })}
          />
          <EditToggle
            label="Has Business"
            value={editForm.has_business}
            onChange={(v) => setEditForm({ ...editForm, has_business: v })}
          />
          <EditToggle
            label="Has Real Estate"
            value={editForm.has_real_estate}
            onChange={(v) => setEditForm({ ...editForm, has_real_estate: v })}
          />
          <EditField
            label="Dependents"
            value={
              editForm.dependents !== null
                ? String(editForm.dependents)
                : ""
            }
            onChange={(v) =>
              setEditForm({
                ...editForm,
                dependents: v === "" ? null : parseInt(v, 10) || 0,
              })
            }
            type="number"
          />
          <EditSelect
            label="Debt Level"
            value={editForm.debt_level}
            options={DEBT_LEVELS}
            onChange={(v) => setEditForm({ ...editForm, debt_level: v })}
          />
          <EditField
            label="Financial Goal"
            value={editForm.financial_goal}
            onChange={(v) => setEditForm({ ...editForm, financial_goal: v })}
          />
          {wealth && (
            <>
              <ComputedField
                label="Wealth Archetype"
                value={wealth.wealth_archetype as string}
              />
              <ComputedField
                label="Plan Phase"
                value={wealth.plan_phase as string}
              />
            </>
          )}
          <EditActions onSave={onSave} onCancel={onCancel} saving={saving} />
        </div>
      ) : !wealth ? (
        <EmptyLayer
          href="/wealth"
          accentText="text-primary"
          linkText="Discover Your Wealth Archetype"
        />
      ) : (() => {
        const wa = wealth.wealth_archetype as Record<string, unknown> | string | null;
        const waName = typeof wa === "object" && wa !== null ? (wa.name as string) : (wa as string);
        const waDesc = typeof wa === "object" && wa !== null ? (wa.description as string) : undefined;
        const levers = wealth.lever_priorities as string[] | null;
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <FieldRow label="Wealth Archetype" value={waName} />
              {waDesc && (
                <p className="font-body text-xs text-text/40 leading-relaxed py-1">
                  {waDesc}
                </p>
              )}
              <FieldRow label="Risk Tolerance" value={wealth.risk_tolerance as string} />
            </div>
            {Array.isArray(levers) && levers.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Lever Priority
                </p>
                <TagList
                  items={levers}
                  accentBg="bg-primary/10"
                  accentText="text-primary"
                />
              </div>
            )}
          </div>
        );
      })()}
    </ProfileSection>
  );
}

// ── Creative Section ──────────────────────────────────────────────

function CreativeSection({ profile }: { profile: ProfileResponse }) {
  const creative = profile.creative;

  return (
    <ProfileSection
      title="Creative Forge"
      accentText="text-secondary-light"
      accentBg="bg-secondary/10"
      accentColor="#9B4DCA"
      footerHref="/creative"
      footerLabel="Explore Creative"
      icon={
        <svg
          className="w-5 h-5 text-secondary-light"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
          <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
          <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
          <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
          <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
        </svg>
      }
    >
      {!creative ? (
        <EmptyLayer
          href="/creative"
          accentText="text-secondary-light"
          linkText="Explore Creative Forge"
        />
      ) : (() => {
        const guilford = creative.guilford_scores as Record<string, number> | undefined;
        const mediums = creative.medium_affinities as string[] | undefined;
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <FieldRow
                label="Creative Orientation"
                value={creative.creative_orientation as string}
              />
              <FieldRow
                label="Production Mode"
                value={creative.preferred_production_mode as string}
              />
            </div>
            {guilford && Object.keys(guilford).length > 0 && (
              <div className="space-y-1">
                {Object.entries(guilford).map(([key, val]) => (
                  <FieldRow
                    key={key}
                    label={key.charAt(0).toUpperCase() + key.slice(1)}
                    value={Math.round(val)}
                  />
                ))}
              </div>
            )}
            {Array.isArray(mediums) && mediums.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Recommended Mediums
                </p>
                <TagList
                  items={mediums}
                  accentBg="bg-secondary/10"
                  accentText="text-secondary-light"
                />
              </div>
            )}
          </div>
        );
      })()}
    </ProfileSection>
  );
}

// ── Perspective Section ───────────────────────────────────────────

function PerspectiveSection({ profile }: { profile: ProfileResponse }) {
  const perspective = profile.perspective;

  return (
    <ProfileSection
      title="Perspective Prism"
      accentText="text-accent"
      accentBg="bg-accent/10"
      accentColor="#7B2D8E"
      footerHref="/perspective"
      footerLabel="Explore Perspective"
      icon={
        <svg
          className="w-5 h-5 text-accent"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
      }
    >
      {!perspective ? (
        <EmptyLayer
          href="/perspective"
          accentText="text-accent"
          linkText="Map Your Perspective"
        />
      ) : (() => {
        const kd = perspective.kegan_description as Record<string, unknown> | undefined;
        const strengths = kd?.strengths as string[] | undefined;
        const growthEdges = kd?.growth_edges as string[] | undefined;
        return (
          <div className="space-y-4">
            <div className="space-y-1">
              <FieldRow
                label="Kegan Stage"
                value={kd?.name as string || perspective.kegan_stage as string}
              />
              {kd?.description != null && (
                <p className="font-body text-xs text-text/40 leading-relaxed py-1">
                  {String(kd.description)}
                </p>
              )}
            </div>
            {Array.isArray(strengths) && strengths.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Strengths
                </p>
                <TagList
                  items={strengths}
                  accentBg="bg-accent/10"
                  accentText="text-accent"
                />
              </div>
            )}
            {Array.isArray(growthEdges) && growthEdges.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Growth Edges
                </p>
                <TagList
                  items={growthEdges}
                  accentBg="bg-white/5"
                  accentText="text-text/50"
                />
              </div>
            )}
          </div>
        );
      })()}
    </ProfileSection>
  );
}

// ── Download helper ───────────────────────────────────────────────

function downloadProfileJson(profile: ProfileResponse, email: string) {
  const exportData = {
    exported_at: new Date().toISOString(),
    email,
    profile,
  };
  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `alchymine-profile-${profile.id.slice(0, 8)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

// ── Report status badge ───────────────────────────────────────────

function ReportStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    complete: "bg-green-500/15 text-green-400 border-green-500/20",
    generating: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
    pending: "bg-blue-500/15 text-blue-400 border-blue-500/20",
    failed: "bg-red-500/15 text-red-400 border-red-500/20",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-[0.65rem] font-body font-medium tracking-wider uppercase border ${styles[status] ?? styles["pending"]}`}
    >
      {status}
    </span>
  );
}

// ── Main Page ─────────────────────────────────────────────────────

function makeIdentityForm(
  profile: ProfileResponse,
): IdentityEditForm {
  const intake = profile.intake;
  return {
    full_name: intake?.full_name ?? "",
    birth_date: intake?.birth_date ?? "",
    birth_time: intake?.birth_time ?? "",
    birth_city: intake?.birth_city ?? "",
  };
}

function makeWealthForm(
  profile: ProfileResponse,
): WealthEditForm {
  // wealth_context may exist on the intake data from the API (not typed on IntakeProfileData)
  const wc = profile.intake?.wealth_context;
  return {
    income_range: wc?.income_range ?? "",
    has_investments: wc?.has_investments ?? null,
    has_business: wc?.has_business ?? null,
    has_real_estate: wc?.has_real_estate ?? null,
    dependents: wc?.dependents ?? null,
    debt_level: wc?.debt_level ?? "",
    financial_goal: wc?.financial_goal ?? "",
  };
}

export default function ProfilePage() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const profileState = useApi<ProfileResponse>(
    () => (userId ? getProfile(userId) : Promise.reject(new Error("No user"))),
    [userId],
  );

  const recentReports = useApi<ReportListResponse>(
    () =>
      userId
        ? listUserReports(userId, { limit: 5 })
        : Promise.reject(new Error("No user")),
    [userId],
  );

  // ── Edit state ──────────────────────────────────────────────────
  const [editingSection, setEditingSection] = useState<EditingSection>(null);
  const [identityForm, setIdentityForm] = useState<IdentityEditForm>({
    full_name: "",
    birth_date: "",
    birth_time: "",
    birth_city: "",
  });
  const [wealthForm, setWealthForm] = useState<WealthEditForm>({
    income_range: "",
    has_investments: null,
    has_business: null,
    has_real_estate: null,
    dependents: null,
    debt_level: "",
    financial_goal: "",
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function startEditIdentity() {
    if (!profileState.data) return;
    setIdentityForm(makeIdentityForm(profileState.data));
    setSaveError(null);
    setEditingSection("identity");
  }

  function startEditWealth() {
    if (!profileState.data) return;
    setWealthForm(makeWealthForm(profileState.data));
    setSaveError(null);
    setEditingSection("wealth");
  }

  function cancelEdit() {
    setEditingSection(null);
    setSaveError(null);
  }

  async function handleSaveIdentity() {
    if (!userId || !profileState.data) return;
    if (!identityForm.full_name.trim() || !identityForm.birth_date) {
      setSaveError("Name and birth date are required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const intake = profileState.data.intake;
      await saveIntake(userId, {
        full_name: identityForm.full_name,
        birth_date: identityForm.birth_date,
        birth_time: identityForm.birth_time || null,
        birth_city: identityForm.birth_city || null,
        intention: intake?.intention ?? "",
        intentions: intake?.intentions ?? [],
      });
      profileState.refetch();
      setEditingSection(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveWealth() {
    if (!userId || !profileState.data) return;
    setSaving(true);
    setSaveError(null);
    try {
      const intake = profileState.data.intake;
      await saveIntake(userId, {
        full_name: intake?.full_name ?? "",
        birth_date: intake?.birth_date ?? "",
        birth_time: intake?.birth_time ?? null,
        birth_city: intake?.birth_city ?? null,
        intention: intake?.intention ?? "",
        intentions: intake?.intentions ?? [],
        wealth_context: {
          income_range: wealthForm.income_range || null,
          has_investments: wealthForm.has_investments,
          has_business: wealthForm.has_business,
          has_real_estate: wealthForm.has_real_estate,
          dependents: wealthForm.dependents,
          debt_level: wealthForm.debt_level || null,
          financial_goal: wealthForm.financial_goal || null,
        },
      });
      profileState.refetch();
      setEditingSection(null);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const [completeness, setCompleteness] = useState<CompletenessResponse | null>(
    null,
  );

  useEffect(() => {
    if (!userId) return;
    getCompleteness(userId)
      .then(setCompleteness)
      .catch(() => {});
  }, [userId]);

  return (
    <ProtectedRoute>
      <div className="grain-overlay bg-atmosphere min-h-screen">
        <main className="px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* ── Header ─────────────────────────────────────────── */}
            <MotionReveal delay={0.05} y={16}>
              <div>
                <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-2">
                  Personal Command Center
                </p>
                <div className="flex items-center justify-between">
                  <h1 className="font-display text-display-md font-light">
                    Your <span className="text-gradient-gold">Profile</span>
                  </h1>
                  <Link
                    href="/discover/intake"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm font-body text-text/50 hover:border-primary/30 hover:text-text/70 transition-all duration-300"
                  >
                    <svg
                      className="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                    </svg>
                    Update Profile
                  </Link>
                </div>
                <p className="font-body text-text/40 text-sm mt-2">
                  All five systems in one place
                </p>
              </div>
              <hr className="rule-gold mt-6 max-w-[80px]" />
            </MotionReveal>

            {/* ── Save error banner ────────────────────────────────── */}
            {saveError && (
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3">
                <p className="font-body text-sm text-red-400">{saveError}</p>
              </div>
            )}

            {/* ── Content ────────────────────────────────────────── */}
            {profileState.loading ? (
              <Spinner />
            ) : profileState.error ? (
              <MotionReveal delay={0.1} y={16}>
                <div className="card-surface p-8 text-center">
                  <p className="font-body text-text/50 mb-2">
                    Unable to load profile data.
                  </p>
                  <p className="font-body text-xs text-text/25 mb-4">
                    Complete the intake assessment to create your profile.
                  </p>
                  <Link
                    href="/discover/intake"
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary/10 border border-primary/20 text-primary font-body text-sm rounded-xl hover:bg-primary/20 transition-colors"
                  >
                    Start Intake Assessment
                  </Link>
                </div>
              </MotionReveal>
            ) : profileState.data ? (
              <MotionStagger staggerDelay={0.1} className="space-y-6">
                <MotionStaggerItem>
                  <IdentitySection
                    profile={profileState.data}
                    editing={editingSection === "identity"}
                    onEdit={startEditIdentity}
                    onCancel={cancelEdit}
                    onSave={handleSaveIdentity}
                    editForm={identityForm}
                    setEditForm={setIdentityForm}
                    saving={saving}
                  />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <HealingSection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <WealthSection
                    profile={profileState.data}
                    editing={editingSection === "wealth"}
                    onEdit={startEditWealth}
                    onCancel={cancelEdit}
                    onSave={handleSaveWealth}
                    editForm={wealthForm}
                    setEditForm={setWealthForm}
                    saving={saving}
                  />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <CreativeSection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <PerspectiveSection profile={profileState.data} />
                </MotionStaggerItem>

                {/* ── Recent Reports ─────────────────────────────── */}
                <MotionStaggerItem>
                  <div className="card-surface px-5 py-5 sm:px-6">
                    <h2 className="font-display text-lg font-light text-text mb-1">
                      Recent Reports
                    </h2>
                    <p className="font-body text-xs text-text/40 mb-4">
                      Your latest transformation reports
                    </p>
                    {recentReports.loading ? (
                      <Spinner />
                    ) : recentReports.error ||
                      !recentReports.data ||
                      recentReports.data.reports.length === 0 ? (
                      <div className="text-center py-4">
                        <p className="font-body text-text/50 text-sm mb-3">
                          No reports yet
                        </p>
                        <Link
                          href="/discover/intake"
                          className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 text-primary font-body text-sm rounded-xl hover:bg-primary/20 transition-colors"
                        >
                          Start Assessment
                        </Link>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {recentReports.data.reports.map((report) => (
                          <Link
                            key={report.id}
                            href={
                              report.status === "complete"
                                ? `/discover/report/${report.id}`
                                : `/discover/generating/${report.id}`
                            }
                            className="block card-surface p-4 transition-all duration-300 hover:brightness-110 hover:-translate-y-0.5"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="min-w-0 flex-1">
                                <p className="font-body text-sm text-text/70 truncate">
                                  Report{" "}
                                  <span className="text-text/30">
                                    {report.id.slice(0, 8)}
                                  </span>
                                </p>
                                <p className="font-body text-xs text-text/30 mt-0.5">
                                  {new Date(
                                    report.created_at,
                                  ).toLocaleDateString(undefined, {
                                    month: "short",
                                    day: "numeric",
                                    year: "numeric",
                                    hour: "numeric",
                                    minute: "2-digit",
                                  })}
                                </p>
                              </div>
                              <ReportStatusBadge status={report.status} />
                            </div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </MotionStaggerItem>

                {/* ── Your Data ───────────────────────────────────── */}
                <MotionStaggerItem>
                  <div className="card-surface px-5 py-5 sm:px-6">
                    <h2 className="font-display text-lg font-light text-text mb-2">
                      Your Data
                    </h2>
                    <p className="font-body text-xs text-text/40 mb-4">
                      Your data belongs to you. Download a complete copy of
                      everything Alchymine knows about you.
                    </p>
                    <button
                      onClick={() =>
                        downloadProfileJson(
                          profileState.data!,
                          user?.email ?? "user",
                        )
                      }
                      className="inline-flex items-center gap-2 px-4 py-2 bg-white/[0.04] border border-white/10 text-text/60 font-body text-sm rounded-lg hover:bg-white/[0.08] hover:text-text transition-colors"
                      aria-label="Download your profile data as JSON"
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
                {completeness && (
                  <MotionStaggerItem>
                    <div className="card-surface p-6">
                      <h3 className="font-display text-lg font-medium mb-4">
                        Assessment Status
                      </h3>
                      <div className="space-y-3">
                        {(
                          [
                            {
                              key: "big_five" as const,
                              label: "Personality (Big Five)",
                              sections: "big_five",
                            },
                            {
                              key: "attachment" as const,
                              label: "Attachment Style",
                              sections: "attachment",
                            },
                            {
                              key: "risk_tolerance" as const,
                              label: "Risk Tolerance",
                              sections: "risk_tolerance",
                            },
                            {
                              key: "enneagram" as const,
                              label: "Enneagram",
                              sections: "enneagram",
                            },
                            {
                              key: "perspective" as const,
                              label: "Perspective (Kegan)",
                              sections: "perspective",
                            },
                            {
                              key: "creativity" as const,
                              label: "Creativity",
                              sections: "creativity",
                            },
                          ] as const
                        ).map(({ key, label, sections }) => {
                          const section = completeness[key] as
                            | { answered: number; total: number; complete: boolean }
                            | undefined;
                          if (!section) return null;
                          return (
                            <div
                              key={key}
                              className="flex items-center justify-between py-2 border-b border-white/[0.06] last:border-0"
                            >
                              <div>
                                <span className="text-sm font-body text-text">
                                  {label}
                                </span>
                                <span className="text-xs text-text/40 ml-2">
                                  {section.answered}/{section.total}
                                </span>
                              </div>
                              {section.complete ? (
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-primary/70">
                                    Complete
                                  </span>
                                  <a
                                    href={`/discover/assessment?sections=${sections}`}
                                    className="text-xs text-text/30 hover:text-text/60 transition-colors"
                                  >
                                    Retake
                                  </a>
                                </div>
                              ) : (
                                <a
                                  href={`/discover/assessment?sections=${sections}`}
                                  className="text-xs font-medium text-primary hover:text-primary-light transition-colors"
                                >
                                  Complete
                                </a>
                              )}
                            </div>
                          );
                        })}
                      </div>
                      <div className="mt-4 pt-3 border-t border-white/[0.06]">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-text/40">Overall</span>
                          <span className="text-xs text-text/50">
                            {completeness.overall_pct}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </MotionStaggerItem>
                )}
              </MotionStagger>
            ) : null}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
