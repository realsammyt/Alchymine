"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useAuth } from "@/lib/AuthContext";
import { useApi } from "@/lib/useApi";
import {
  getProfile,
  getCompleteness,
  ProfileResponse,
  type CompletenessResponse,
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
  accentBorder,
  icon,
  children,
}: {
  title: string;
  accentText: string;
  accentBg: string;
  accentBorder: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className={`card-surface border ${accentBorder} p-6`}>
      <div className="flex items-center gap-3 mb-5">
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
      {children}
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

// ── Identity Section ──────────────────────────────────────────────

function IdentitySection({ profile }: { profile: ProfileResponse }) {
  const identity = profile.identity;
  const intake = profile.intake;

  const hasData = !!(identity || intake);

  return (
    <ProfileSection
      title="Personal Intelligence"
      accentText="text-primary"
      accentBg="bg-primary/10"
      accentBorder="border-primary/20"
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
    >
      {!hasData ? (
        <EmptyLayer
          href="/intelligence"
          accentText="text-primary"
          linkText="Explore Personal Intelligence"
        />
      ) : (
        <div className="space-y-1">
          {intake && (
            <>
              <FieldRow label="Name" value={intake.full_name} />
              <FieldRow label="Birth Date" value={intake.birth_date} />
              <FieldRow label="Birth Time" value={intake.birth_time} />
              <FieldRow label="Birth City" value={intake.birth_city} />
            </>
          )}
          {identity && (
            <>
              <FieldRow
                label="Life Path"
                value={identity.life_path as number}
              />
              <FieldRow
                label="Expression"
                value={identity.expression as number}
              />
              <FieldRow
                label="Soul Urge"
                value={identity.soul_urge as number}
              />
              <FieldRow label="Sun Sign" value={identity.sun_sign as string} />
              <FieldRow
                label="Moon Sign"
                value={identity.moon_sign as string}
              />
              <FieldRow
                label="Archetype"
                value={identity.primary_archetype as string}
              />
            </>
          )}
        </div>
      )}
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
      accentBorder="border-accent/20"
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
      ) : (
        <div className="space-y-4">
          <div className="space-y-1">
            <FieldRow
              label="Breathwork Preference"
              value={healing.breathwork_preference as string}
            />
            <FieldRow
              label="Attachment Style"
              value={healing.attachment_style as string}
            />
          </div>
          {Array.isArray(healing.active_modalities) &&
            healing.active_modalities.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Active Modalities
                </p>
                <TagList
                  items={healing.active_modalities as string[]}
                  accentBg="bg-accent/10"
                  accentText="text-accent"
                />
              </div>
            )}
        </div>
      )}
    </ProfileSection>
  );
}

// ── Wealth Section ────────────────────────────────────────────────

function WealthSection({ profile }: { profile: ProfileResponse }) {
  const wealth = profile.wealth;

  return (
    <ProfileSection
      title="Generational Wealth"
      accentText="text-primary"
      accentBg="bg-primary/10"
      accentBorder="border-primary/20"
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
    >
      {!wealth ? (
        <EmptyLayer
          href="/wealth"
          accentText="text-primary"
          linkText="Discover Your Wealth Archetype"
        />
      ) : (
        <div className="space-y-4">
          <div className="space-y-1">
            <FieldRow
              label="Wealth Archetype"
              value={wealth.wealth_archetype as string}
            />
            <FieldRow label="Plan Phase" value={wealth.plan_phase as string} />
          </div>
          {Array.isArray(wealth.primary_levers) &&
            wealth.primary_levers.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Lever Focus
                </p>
                <TagList
                  items={wealth.primary_levers as string[]}
                  accentBg="bg-primary/10"
                  accentText="text-primary"
                />
              </div>
            )}
        </div>
      )}
    </ProfileSection>
  );
}

// ── Creative Section ──────────────────────────────────────────────

function CreativeSection({ profile }: { profile: ProfileResponse }) {
  const creative = profile.creative;

  const guilfordFields: Array<{ label: string; key: string }> = [
    { label: "Fluency", key: "guilford_fluency" },
    { label: "Flexibility", key: "guilford_flexibility" },
    { label: "Originality", key: "guilford_originality" },
    { label: "Elaboration", key: "guilford_elaboration" },
    { label: "Sensitivity", key: "guilford_sensitivity" },
    { label: "Redefinition", key: "guilford_redefinition" },
  ];

  return (
    <ProfileSection
      title="Creative Forge"
      accentText="text-secondary-light"
      accentBg="bg-secondary/10"
      accentBorder="border-secondary/20"
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
      ) : (
        <div className="space-y-4">
          <div className="space-y-1">
            <FieldRow
              label="Creative Style"
              value={creative.creative_style as string}
            />
            <FieldRow
              label="Overall Score"
              value={
                typeof creative.overall_score === "number"
                  ? (creative.overall_score as number).toFixed(1)
                  : undefined
              }
            />
          </div>
          <div className="space-y-1">
            {guilfordFields.map(({ label, key }) =>
              creative[key] !== undefined && creative[key] !== null ? (
                <FieldRow
                  key={key}
                  label={`Guilford: ${label}`}
                  value={
                    typeof creative[key] === "number"
                      ? (creative[key] as number).toFixed(1)
                      : (creative[key] as string)
                  }
                />
              ) : null,
            )}
          </div>
        </div>
      )}
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
      accentBorder="border-accent/20"
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
      ) : (
        <div className="space-y-4">
          <div className="space-y-1">
            <FieldRow
              label="Kegan Stage"
              value={perspective.kegan_stage as string | number}
            />
            <FieldRow
              label="Stage Name"
              value={perspective.kegan_stage_name as string}
            />
          </div>
          {Array.isArray(perspective.detected_biases) &&
            perspective.detected_biases.length > 0 && (
              <div>
                <p className="font-body text-xs text-text/40 uppercase tracking-wide mb-2">
                  Detected Biases
                </p>
                <TagList
                  items={perspective.detected_biases as string[]}
                  accentBg="bg-accent/10"
                  accentText="text-accent"
                />
              </div>
            )}
        </div>
      )}
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

// ── Main Page ─────────────────────────────────────────────────────

export default function ProfilePage() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const profileState = useApi<ProfileResponse>(
    () => (userId ? getProfile(userId) : Promise.reject(new Error("No user"))),
    [userId],
  );

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
              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
                <div>
                  <p className="text-xs font-body font-medium text-primary/70 uppercase tracking-[0.2em] mb-2">
                    Personal Command Center
                  </p>
                  <h1 className="font-display text-display-md font-light">
                    Your <span className="text-gradient-gold">Profile</span>
                  </h1>
                  <p className="font-body text-text/40 text-sm mt-2">
                    All five systems in one place
                  </p>
                </div>

                {profileState.data && (
                  <button
                    onClick={() =>
                      downloadProfileJson(
                        profileState.data!,
                        user?.email ?? "user",
                      )
                    }
                    className="inline-flex items-center gap-2 px-4 py-2.5 min-h-[44px] bg-primary/10 border border-primary/20 text-primary font-body text-sm rounded-xl hover:bg-primary/20 transition-colors self-start sm:self-auto"
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
                    Download Your Data
                  </button>
                )}
              </div>
              <hr className="rule-gold mt-6 max-w-[80px]" />
            </MotionReveal>

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
                  <IdentitySection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <HealingSection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <WealthSection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <CreativeSection profile={profileState.data} />
                </MotionStaggerItem>
                <MotionStaggerItem>
                  <PerspectiveSection profile={profileState.data} />
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
                          const section = completeness[key];
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
