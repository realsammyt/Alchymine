"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getReport, ApiError, ReportResponse, IdentityLayer } from "@/lib/api";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

// ─── Helper components ───────────────────────────────────────────────

function TraitBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-body text-text/50 w-36 text-right">
        {label}
      </span>
      <div
        className="flex-1 h-2 bg-white/[0.04] rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${Math.round(value)} out of 100`}
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-700"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-sm font-display font-medium text-primary w-10 text-right">
        {Math.round(value)}
      </span>
    </div>
  );
}

function NumberCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: number | string;
  subtitle?: string;
}) {
  return (
    <div className="card-surface p-4 text-center">
      <div className="font-display text-3xl font-light text-gradient-gold mb-1">
        {value}
      </div>
      <div className="text-sm font-body font-medium text-text/70">{label}</div>
      {subtitle && (
        <div className="text-[0.65rem] font-body text-text/30 mt-1 tracking-wide">
          {subtitle}
        </div>
      )}
    </div>
  );
}

function SystemSummaryCard({
  title,
  children,
  disclaimers,
}: {
  title: string;
  children: React.ReactNode;
  disclaimers?: string[];
}) {
  return (
    <div className="card-surface p-6">
      <h3 className="font-display text-lg font-light text-text/80 mb-4">
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
      {disclaimers && disclaimers.length > 0 && (
        <div className="mt-4 pt-3 border-t border-white/[0.04]">
          {disclaimers.map((d, i) => (
            <p
              key={i}
              className="text-[0.65rem] font-body text-text/25 leading-relaxed"
            >
              {d}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReport() {
      try {
        const data = await getReport(reportId);
        setReport(data);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 202) {
            router.replace(`/discover/generating/${reportId}`);
            return;
          }
          setError(err.message);
        } else {
          setError("Failed to load report");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchReport();
  }, [reportId, router]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div
            className="w-12 h-12 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto mb-4"
            aria-hidden="true"
          />
          <p className="text-text/40 font-body">Loading your report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center">
            <svg
              className="w-7 h-7 text-primary/60"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h2 className="font-display text-xl font-light text-text mb-2">
            Could not load report
          </h2>
          <p className="text-text/40 font-body text-sm mb-6">{error}</p>
          <Button onClick={() => router.push("/discover/intake")}>
            Start Over
          </Button>
        </div>
      </div>
    );
  }

  const profileSummary = report?.result?.profile_summary as
    | Record<string, unknown>
    | undefined;

  const identity = profileSummary?.identity as
    | IdentityLayer
    | undefined;
  const healingSummary = profileSummary?.healing as
    | {
        recommended_modalities?: Array<{
          modality: string;
          preference_score?: number;
        }>;
        crisis_flag?: boolean;
        disclaimers?: string[];
      }
    | undefined;
  const wealthSummary = profileSummary?.wealth as
    | {
        wealth_archetype?: { name: string; description?: string };
        lever_priorities?: string[];
        disclaimers?: string[];
      }
    | undefined;
  const creativeSummary = profileSummary?.creative as
    | {
        creative_orientation?: { style?: string; summary?: string };
        strengths?: string[];
      }
    | undefined;
  const perspectiveSummary = profileSummary?.perspective as
    | {
        detected_biases?: Array<{ bias_name: string }>;
        kegan_stage?: { stage?: number; name?: string; description?: string };
      }
    | undefined;

  return (
    <div className="flex-1 px-4 sm:px-6 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Report Header */}
        <MotionReveal>
          <div className="text-center mb-14">
            <p className="text-[0.65rem] font-body font-medium uppercase tracking-[0.2em] text-primary/60 mb-4">
              Your Alchymine Report
            </p>
            <h1 className="font-display text-display-lg font-light mb-4">
              <span className="text-gradient-gold">Identity</span>{" "}
              <span className="text-text/60">Profile</span>
            </h1>
            <hr className="rule-gold my-6 max-w-[80px] mx-auto" />
            <p className="text-text/40 font-body max-w-xl mx-auto leading-relaxed">
              Your unique identity mapped through numerology, astrology,
              archetypes, and personality science — the foundation for all five
              Alchymine systems.
            </p>
          </div>
        </MotionReveal>

        {identity ? (
          <div className="space-y-8">
            {/* ── Numerology Module ─────────────────────────────────── */}
            <MotionReveal delay={0.1}>
              <Card
                title="Numerology"
                subtitle="Pythagorean numerology calculations from your name and birth date"
                expandable
                expandedContent={
                  <div className="text-sm font-body text-text/40 space-y-2">
                    <p>
                      <strong className="text-text/60">Methodology:</strong>{" "}
                      Pythagorean numerology reduces your full birth name and
                      date to single-digit (or master number) archetypes. Each
                      number 1-9 (plus 11, 22, 33) carries a vibrational
                      meaning.
                    </p>
                    <p>
                      <strong className="text-text/60">Source:</strong>{" "}
                      Deterministic calculation — no AI involved.
                    </p>
                  </div>
                }
              >
                <MotionStagger
                  staggerDelay={0.06}
                  className="grid grid-cols-2 sm:grid-cols-3 gap-4"
                >
                  <MotionStaggerItem>
                    <NumberCard
                      label="Life Path"
                      value={identity.numerology.life_path}
                      subtitle={
                        identity.numerology.is_master_number
                          ? "Master Number"
                          : undefined
                      }
                    />
                  </MotionStaggerItem>
                  <MotionStaggerItem>
                    <NumberCard
                      label="Expression"
                      value={identity.numerology.expression}
                      subtitle="Destiny Number"
                    />
                  </MotionStaggerItem>
                  <MotionStaggerItem>
                    <NumberCard
                      label="Soul Urge"
                      value={identity.numerology.soul_urge}
                      subtitle="Heart's Desire"
                    />
                  </MotionStaggerItem>
                  <MotionStaggerItem>
                    <NumberCard
                      label="Personality"
                      value={identity.numerology.personality}
                      subtitle="Outer Number"
                    />
                  </MotionStaggerItem>
                  <MotionStaggerItem>
                    <NumberCard
                      label="Personal Year"
                      value={identity.numerology.personal_year}
                      subtitle="Current Cycle"
                    />
                  </MotionStaggerItem>
                  <MotionStaggerItem>
                    <NumberCard
                      label="Maturity"
                      value={identity.numerology.maturity ?? "—"}
                    />
                  </MotionStaggerItem>
                </MotionStagger>
              </Card>
            </MotionReveal>

            {/* ── Astrology Module ──────────────────────────────────── */}
            <MotionReveal delay={0.15}>
              <Card
                title="Astrology"
                subtitle="Natal chart positions from Swiss Ephemeris"
                expandable
                expandedContent={
                  <div className="text-sm font-body text-text/40 space-y-2">
                    <p>
                      <strong className="text-text/60">Methodology:</strong>{" "}
                      Planetary positions calculated using the Swiss Ephemeris
                      library for your exact birth date.
                    </p>
                    <p>
                      <strong className="text-text/60">Source:</strong>{" "}
                      Deterministic astronomical calculation — no AI
                      interpretation.
                    </p>
                  </div>
                }
              >
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <NumberCard
                    label="Sun Sign"
                    value={identity.astrology.sun_sign}
                  />
                  <NumberCard
                    label="Moon Sign"
                    value={identity.astrology.moon_sign}
                  />
                  <NumberCard
                    label="Rising Sign"
                    value={identity.astrology.rising_sign ?? "N/A"}
                    subtitle={
                      !identity.astrology.rising_sign
                        ? "Birth time required"
                        : undefined
                    }
                  />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {identity.astrology.mercury_retrograde && (
                    <span className="px-3 py-1.5 bg-accent/[0.06] text-accent font-body text-[0.7rem] tracking-wider uppercase rounded-full border border-accent/[0.12]">
                      Mercury Retrograde
                    </span>
                  )}
                  {identity.astrology.venus_retrograde && (
                    <span className="px-3 py-1.5 bg-secondary/[0.06] text-secondary-light font-body text-[0.7rem] tracking-wider uppercase rounded-full border border-secondary/[0.12]">
                      Venus Retrograde
                    </span>
                  )}
                </div>
              </Card>
            </MotionReveal>

            {/* ── Archetype Module ──────────────────────────────────── */}
            <MotionReveal delay={0.2}>
              <Card
                title="Archetype"
                subtitle="Jungian archetype mapping from numerology and astrology signals"
                expandable
                expandedContent={
                  <div className="text-sm font-body text-text/40 space-y-2">
                    <p>
                      <strong className="text-text/60">Methodology:</strong>{" "}
                      Your primary archetype is determined by Life Path number,
                      with elemental boosts from your Sun sign.
                    </p>
                    <p>
                      <strong className="text-text/60">Framework:</strong> 12
                      Jungian archetypes: Creator, Sage, Explorer, Mystic,
                      Ruler, Lover, Hero, Caregiver, Jester, Innocent, Rebel,
                      Everyman.
                    </p>
                  </div>
                }
              >
                <div className="space-y-4">
                  <div className="flex flex-wrap gap-3">
                    <div className="px-4 py-2.5 bg-primary/[0.06] border border-primary/[0.15] rounded-xl">
                      <span className="text-[0.65rem] font-body text-primary/50 tracking-wider uppercase block">
                        Primary
                      </span>
                      <span className="font-display text-lg font-medium text-primary capitalize">
                        {identity.archetype.primary}
                      </span>
                    </div>
                    {identity.archetype.secondary && (
                      <div className="px-4 py-2.5 bg-secondary/[0.06] border border-secondary/[0.15] rounded-xl">
                        <span className="text-[0.65rem] font-body text-secondary-light/50 tracking-wider uppercase block">
                          Secondary
                        </span>
                        <span className="font-display text-lg font-medium text-secondary-light capitalize">
                          {identity.archetype.secondary}
                        </span>
                      </div>
                    )}
                    <div className="px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl">
                      <span className="text-[0.65rem] font-body text-text/30 tracking-wider uppercase block">
                        Shadow
                      </span>
                      <span className="font-display text-lg font-medium text-text/50">
                        {identity.archetype.shadow}
                      </span>
                    </div>
                  </div>

                  {identity.archetype.light_qualities.length > 0 && (
                    <div>
                      <p className="text-[0.65rem] font-body text-text/30 mb-2 uppercase tracking-[0.15em]">
                        Light Qualities
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {identity.archetype.light_qualities.map((q) => (
                          <span
                            key={q}
                            className="px-3 py-1.5 bg-primary/[0.04] border border-primary/[0.1] rounded-full text-sm font-body text-text/60"
                          >
                            {q}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {identity.archetype.shadow_qualities.length > 0 && (
                    <div>
                      <p className="text-[0.65rem] font-body text-text/30 mb-2 uppercase tracking-[0.15em]">
                        Shadow Qualities
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {identity.archetype.shadow_qualities.map((q) => (
                          <span
                            key={q}
                            className="px-3 py-1.5 bg-white/[0.03] border border-white/[0.06] rounded-full text-sm font-body text-text/40"
                          >
                            {q}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </MotionReveal>

            {/* ── Personality Module ─────────────────────────────────── */}
            <MotionReveal delay={0.25}>
              <Card
                title="Personality"
                subtitle="Big Five traits from the mini-IPIP assessment"
                expandable
                expandedContent={
                  <div className="text-sm font-body text-text/40 space-y-2">
                    <p>
                      <strong className="text-text/60">Methodology:</strong> The
                      mini-IPIP is a validated 20-item short form of the
                      International Personality Item Pool Big Five factor
                      markers (Donnellan et al., 2006).
                    </p>
                    <p>
                      <strong className="text-text/60">Scale:</strong> Each
                      trait is scored 0-100. Higher scores indicate stronger
                      expression.
                    </p>
                  </div>
                }
              >
                <div className="space-y-4">
                  <div className="space-y-3">
                    <TraitBar
                      label="Openness"
                      value={identity.personality.big_five.openness}
                    />
                    <TraitBar
                      label="Conscientiousness"
                      value={identity.personality.big_five.conscientiousness}
                    />
                    <TraitBar
                      label="Extraversion"
                      value={identity.personality.big_five.extraversion}
                    />
                    <TraitBar
                      label="Agreeableness"
                      value={identity.personality.big_five.agreeableness}
                    />
                    <TraitBar
                      label="Neuroticism"
                      value={identity.personality.big_five.neuroticism}
                    />
                  </div>

                  <div className="pt-4 border-t border-white/[0.04]">
                    <div className="flex flex-wrap gap-3">
                      <div className="px-4 py-2.5 bg-accent/[0.06] border border-accent/[0.15] rounded-xl">
                        <span className="text-[0.65rem] font-body text-accent/50 tracking-wider uppercase block">
                          Attachment Style
                        </span>
                        <span className="font-display text-base font-medium text-accent capitalize">
                          {identity.personality.attachment_style.replace(
                            "-",
                            " / ",
                          )}
                        </span>
                      </div>
                      {identity.personality.enneagram_type && (
                        <div className="px-4 py-2.5 bg-secondary/[0.06] border border-secondary/[0.15] rounded-xl">
                          <span className="text-[0.65rem] font-body text-secondary-light/50 tracking-wider uppercase block">
                            Enneagram
                          </span>
                          <span className="font-display text-base font-medium text-secondary-light">
                            Type {identity.personality.enneagram_type}
                            {identity.personality.enneagram_wing
                              ? `w${identity.personality.enneagram_wing}`
                              : ""}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </MotionReveal>

            {/* ── Strengths Map ──────────────────────────────────────── */}
            {identity.strengths_map && identity.strengths_map.length > 0 && (
              <MotionReveal delay={0.3}>
                <Card
                  title="Strengths Map"
                  subtitle="Top strengths derived from all identity systems"
                >
                  <div className="flex flex-wrap gap-2">
                    {identity.strengths_map.map((strength) => (
                      <span
                        key={strength}
                        className="px-4 py-2 bg-gradient-to-r from-primary/[0.08] to-primary/[0.03] border border-primary/[0.12] rounded-xl text-sm font-body font-medium text-primary"
                      >
                        {strength}
                      </span>
                    ))}
                  </div>
                </Card>
              </MotionReveal>
            )}

            {/* ── Other Systems ──────────────────────────────────────── */}
            <MotionReveal delay={0.35}>
              <div className="pt-4">
                <h2 className="section-heading-sm text-text/30 mb-6">
                  Other Systems
                </h2>
                <MotionStagger
                  staggerDelay={0.08}
                  className="grid grid-cols-1 sm:grid-cols-2 gap-4"
                >
                  {/* Healing */}
                  <MotionStaggerItem>
                    <SystemSummaryCard
                      title="Healing — Ethical Healing"
                      disclaimers={healingSummary?.disclaimers}
                    >
                      {healingSummary?.recommended_modalities &&
                      healingSummary.recommended_modalities.length > 0 ? (
                        <>
                          <p className="text-[0.65rem] font-body text-text/30 uppercase tracking-[0.15em]">
                            Recommended Modalities
                          </p>
                          <ul className="space-y-1.5">
                            {healingSummary.recommended_modalities.map(
                              (m, i) => (
                                <li
                                  key={i}
                                  className="flex items-center justify-between text-sm font-body"
                                >
                                  <span className="text-text/70">
                                    {m.modality}
                                  </span>
                                  {m.preference_score !== undefined && (
                                    <span className="text-primary font-display font-medium text-xs">
                                      {Math.round(m.preference_score)}
                                    </span>
                                  )}
                                </li>
                              ),
                            )}
                          </ul>
                          {healingSummary.crisis_flag && (
                            <div className="mt-2 px-3 py-2 bg-accent/[0.08] border border-accent/[0.15] rounded-lg">
                              <span className="text-[0.7rem] font-body text-accent font-medium">
                                Crisis support resources recommended
                              </span>
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-sm font-body text-text/30">
                          Data not yet available
                        </p>
                      )}
                    </SystemSummaryCard>
                  </MotionStaggerItem>

                  {/* Wealth */}
                  <MotionStaggerItem>
                    <SystemSummaryCard
                      title="Wealth — Generational Wealth"
                      disclaimers={wealthSummary?.disclaimers}
                    >
                      {wealthSummary?.wealth_archetype ? (
                        <>
                          <div className="px-4 py-2.5 bg-primary/[0.06] border border-primary/[0.15] rounded-xl inline-block">
                            <span className="text-[0.65rem] font-body text-primary/50 tracking-wider uppercase block">
                              Wealth Archetype
                            </span>
                            <span className="font-display text-base font-medium text-primary">
                              {wealthSummary.wealth_archetype.name}
                            </span>
                          </div>
                          {wealthSummary.wealth_archetype.description && (
                            <p className="text-sm font-body text-text/50 leading-relaxed">
                              {wealthSummary.wealth_archetype.description}
                            </p>
                          )}
                          {wealthSummary.lever_priorities &&
                            wealthSummary.lever_priorities.length > 0 && (
                              <div>
                                <p className="text-[0.65rem] font-body text-text/30 mb-2 uppercase tracking-[0.15em]">
                                  Priority Levers
                                </p>
                                <ol className="space-y-1">
                                  {wealthSummary.lever_priorities.map(
                                    (lever, i) => (
                                      <li
                                        key={i}
                                        className="flex items-center gap-2 text-sm font-body text-text/60"
                                      >
                                        <span className="text-[0.65rem] font-display text-primary/50 w-4 text-right">
                                          {i + 1}.
                                        </span>
                                        {lever}
                                      </li>
                                    ),
                                  )}
                                </ol>
                              </div>
                            )}
                        </>
                      ) : (
                        <p className="text-sm font-body text-text/30">
                          Data not yet available
                        </p>
                      )}
                    </SystemSummaryCard>
                  </MotionStaggerItem>

                  {/* Creative */}
                  <MotionStaggerItem>
                    <SystemSummaryCard title="Creative — Creative Forge">
                      {creativeSummary?.creative_orientation ? (
                        <>
                          {creativeSummary.creative_orientation.style && (
                            <div className="px-4 py-2.5 bg-secondary/[0.06] border border-secondary/[0.15] rounded-xl inline-block">
                              <span className="text-[0.65rem] font-body text-secondary-light/50 tracking-wider uppercase block">
                                Creative Style
                              </span>
                              <span className="font-display text-base font-medium text-secondary-light">
                                {creativeSummary.creative_orientation.style}
                              </span>
                            </div>
                          )}
                          {creativeSummary.creative_orientation.summary && (
                            <p className="text-sm font-body text-text/50 leading-relaxed">
                              {creativeSummary.creative_orientation.summary}
                            </p>
                          )}
                          {creativeSummary.strengths &&
                            creativeSummary.strengths.length > 0 && (
                              <div>
                                <p className="text-[0.65rem] font-body text-text/30 mb-2 uppercase tracking-[0.15em]">
                                  Strengths
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  {creativeSummary.strengths.map((s) => (
                                    <span
                                      key={s}
                                      className="px-3 py-1.5 bg-primary/[0.04] border border-primary/[0.1] rounded-full text-sm font-body text-text/60"
                                    >
                                      {s}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                        </>
                      ) : (
                        <p className="text-sm font-body text-text/30">
                          Data not yet available
                        </p>
                      )}
                    </SystemSummaryCard>
                  </MotionStaggerItem>

                  {/* Perspective */}
                  <MotionStaggerItem>
                    <SystemSummaryCard title="Perspective — Perspective Prism">
                      {perspectiveSummary?.kegan_stage ||
                      (perspectiveSummary?.detected_biases &&
                        perspectiveSummary.detected_biases.length > 0) ? (
                        <>
                          {perspectiveSummary.kegan_stage && (
                            <div className="px-4 py-2.5 bg-accent/[0.06] border border-accent/[0.15] rounded-xl">
                              <span className="text-[0.65rem] font-body text-accent/50 tracking-wider uppercase block">
                                Kegan Stage
                              </span>
                              <span className="font-display text-base font-medium text-accent">
                                {perspectiveSummary.kegan_stage.name ??
                                  `Stage ${perspectiveSummary.kegan_stage.stage}`}
                              </span>
                              {perspectiveSummary.kegan_stage.description && (
                                <p className="text-[0.7rem] font-body text-text/40 mt-1 leading-relaxed">
                                  {perspectiveSummary.kegan_stage.description}
                                </p>
                              )}
                            </div>
                          )}
                          {perspectiveSummary.detected_biases &&
                            perspectiveSummary.detected_biases.length > 0 && (
                              <div>
                                <p className="text-[0.65rem] font-body text-text/30 mb-2 uppercase tracking-[0.15em]">
                                  Detected Biases
                                </p>
                                <ul className="space-y-1">
                                  {perspectiveSummary.detected_biases.map(
                                    (b, i) => (
                                      <li
                                        key={i}
                                        className="text-sm font-body text-text/60"
                                      >
                                        {b.bias_name}
                                      </li>
                                    ),
                                  )}
                                </ul>
                              </div>
                            )}
                        </>
                      ) : (
                        <p className="text-sm font-body text-text/30">
                          Data not yet available
                        </p>
                      )}
                    </SystemSummaryCard>
                  </MotionStaggerItem>
                </MotionStagger>
              </div>
            </MotionReveal>
          </div>
        ) : (
          <MotionReveal>
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center">
                <svg
                  className="w-7 h-7 text-primary/60"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h2 className="font-display text-xl font-light text-text mb-2">
                Report Generated
              </h2>
              <p className="text-text/40 font-body text-sm mb-2 max-w-md mx-auto">
                Your report has been created but the identity layer has not been
                populated yet.
              </p>
              <p className="text-text/25 font-body text-xs">
                Some sections may still be generating.
              </p>
            </div>
          </MotionReveal>
        )}

        {/* Actions */}
        <MotionReveal delay={0.4}>
          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              variant="ghost"
              onClick={async () => {
                try {
                  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
                  const response = await fetch(
                    `${apiUrl}/api/v1/reports/${reportId}/pdf`,
                    { credentials: "include" },
                  );
                  if (!response.ok) {
                    alert(
                      response.status === 404
                        ? "PDF has not been generated yet. Please try again shortly."
                        : "Failed to download PDF. Please try again.",
                    );
                    return;
                  }
                  const blob = await response.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `alchymine-report-${reportId}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  URL.revokeObjectURL(url);
                  a.remove();
                } catch {
                  alert("Network error — could not download PDF.");
                }
              }}
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
              Export PDF
            </Button>
            <Button onClick={() => router.push("/")}>Back to Home</Button>
          </div>
        </MotionReveal>
      </div>
    </div>
  );
}
