"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getReport, ApiError, ReportResponse, IdentityLayer } from "@/lib/api";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";

// ─── Helper components ───────────────────────────────────────────────

function TraitBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-text/60 w-36 text-right">{label}</span>
      <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary-dark to-primary transition-all duration-700"
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-sm font-mono text-primary w-10">
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
    <div className="bg-surface/50 border border-white/5 rounded-xl p-4 text-center">
      <div className="text-3xl font-bold text-gradient-gold mb-1">{value}</div>
      <div className="text-sm font-medium text-text/80">{label}</div>
      {subtitle && <div className="text-xs text-text/40 mt-1">{subtitle}</div>}
    </div>
  );
}

function ComingSoonSection({ title }: { title: string }) {
  return (
    <div className="card-surface p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-surface/80 backdrop-blur-sm z-10 flex items-center justify-center">
        <span className="px-4 py-2 bg-secondary/20 text-secondary rounded-full text-sm font-medium border border-secondary/20">
          Coming Soon
        </span>
      </div>
      <h3 className="text-lg font-semibold mb-2 text-text/30">{title}</h3>
      <div className="space-y-2">
        <div className="h-4 bg-white/5 rounded w-3/4" />
        <div className="h-4 bg-white/5 rounded w-1/2" />
        <div className="h-4 bg-white/5 rounded w-2/3" />
      </div>
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
            // Still generating — redirect back
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
          <div className="w-12 h-12 rounded-full border-2 border-primary border-t-transparent animate-spin mx-auto mb-4" />
          <p className="text-text/50">Loading your report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold mb-2">Could not load report</h2>
          <p className="text-text/50 mb-6">{error}</p>
          <Button onClick={() => router.push("/discover/intake")}>
            Start Over
          </Button>
        </div>
      </div>
    );
  }

  // Extract identity layer from profile_summary
  const identity = report?.profile_summary?.identity as
    | IdentityLayer
    | undefined;

  return (
    <div className="flex-1 px-6 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Report Header */}
        <div className="text-center mb-12">
          <p className="text-sm uppercase tracking-[0.2em] text-primary mb-3">
            Your Alchymine Report
          </p>
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">
            <span className="text-gradient-gold">Identity</span> Profile
          </h1>
          <p className="text-text/50 max-w-xl mx-auto">
            Your unique identity mapped through numerology, astrology,
            archetypes, and personality science — the foundation for all five
            Alchymine systems.
          </p>
        </div>

        {identity ? (
          <div className="space-y-8">
            {/* ── Numerology Module ─────────────────────────────────── */}
            <Card
              title="Numerology"
              subtitle="Pythagorean numerology calculations from your name and birth date"
              expandable
              expandedContent={
                <div className="text-sm text-text/50 space-y-2">
                  <p>
                    <strong className="text-text/70">Methodology:</strong>{" "}
                    Pythagorean numerology reduces your full birth name and date
                    to single-digit (or master number) archetypes. Each number
                    1-9 (plus 11, 22, 33) carries a vibrational meaning.
                  </p>
                  <p>
                    <strong className="text-text/70">Source:</strong>{" "}
                    Deterministic calculation — no AI involved. Based on the
                    Pythagorean system with standard letter-to-number mapping.
                  </p>
                </div>
              }
            >
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <NumberCard
                  label="Life Path"
                  value={identity.numerology.life_path}
                  subtitle={
                    identity.numerology.is_master_number
                      ? "Master Number"
                      : undefined
                  }
                />
                <NumberCard
                  label="Expression"
                  value={identity.numerology.expression}
                  subtitle="Destiny Number"
                />
                <NumberCard
                  label="Soul Urge"
                  value={identity.numerology.soul_urge}
                  subtitle="Heart's Desire"
                />
                <NumberCard
                  label="Personality"
                  value={identity.numerology.personality}
                  subtitle="Outer Number"
                />
                <NumberCard
                  label="Personal Year"
                  value={identity.numerology.personal_year}
                  subtitle="Current Cycle"
                />
                <NumberCard
                  label="Maturity"
                  value={identity.numerology.maturity ?? "—"}
                />
              </div>
            </Card>

            {/* ── Astrology Module ──────────────────────────────────── */}
            <Card
              title="Astrology"
              subtitle="Natal chart positions from Swiss Ephemeris"
              expandable
              expandedContent={
                <div className="text-sm text-text/50 space-y-2">
                  <p>
                    <strong className="text-text/70">Methodology:</strong>{" "}
                    Planetary positions calculated using the Swiss Ephemeris
                    library for your exact birth date. Rising sign requires
                    birth time.
                  </p>
                  <p>
                    <strong className="text-text/70">Source:</strong>{" "}
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
                  <span className="px-3 py-1 bg-accent/10 text-accent rounded-full text-xs">
                    Mercury Retrograde
                  </span>
                )}
                {identity.astrology.venus_retrograde && (
                  <span className="px-3 py-1 bg-secondary/10 text-secondary rounded-full text-xs">
                    Venus Retrograde
                  </span>
                )}
              </div>
            </Card>

            {/* ── Archetype Module ──────────────────────────────────── */}
            <Card
              title="Archetype"
              subtitle="Jungian archetype mapping from numerology and astrology signals"
              expandable
              expandedContent={
                <div className="text-sm text-text/50 space-y-2">
                  <p>
                    <strong className="text-text/70">Methodology:</strong> Your
                    primary archetype is determined by Life Path number, with
                    elemental boosts from your Sun sign. The shadow pattern is
                    the primary growth edge associated with your archetype.
                  </p>
                  <p>
                    <strong className="text-text/70">Framework:</strong> 12
                    Jungian archetypes: Creator, Sage, Explorer, Mystic, Ruler,
                    Lover, Hero, Caregiver, Jester, Innocent, Rebel, Everyman.
                  </p>
                </div>
              }
            >
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <div className="px-4 py-2 bg-primary/10 border border-primary/20 rounded-xl">
                    <span className="text-xs text-primary/60 block">
                      Primary
                    </span>
                    <span className="text-lg font-semibold text-primary capitalize">
                      {identity.archetype.primary}
                    </span>
                  </div>
                  {identity.archetype.secondary && (
                    <div className="px-4 py-2 bg-secondary/10 border border-secondary/20 rounded-xl">
                      <span className="text-xs text-secondary/60 block">
                        Secondary
                      </span>
                      <span className="text-lg font-semibold text-secondary capitalize">
                        {identity.archetype.secondary}
                      </span>
                    </div>
                  )}
                  <div className="px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-xl">
                    <span className="text-xs text-red-400/60 block">
                      Shadow
                    </span>
                    <span className="text-lg font-semibold text-red-400">
                      {identity.archetype.shadow}
                    </span>
                  </div>
                </div>

                {identity.archetype.light_qualities.length > 0 && (
                  <div>
                    <p className="text-xs text-text/40 mb-2 uppercase tracking-wider">
                      Light Qualities
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {identity.archetype.light_qualities.map((q) => (
                        <span
                          key={q}
                          className="px-3 py-1 bg-primary/5 border border-primary/10 rounded-full text-sm text-text/70"
                        >
                          {q}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {identity.archetype.shadow_qualities.length > 0 && (
                  <div>
                    <p className="text-xs text-text/40 mb-2 uppercase tracking-wider">
                      Shadow Qualities
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {identity.archetype.shadow_qualities.map((q) => (
                        <span
                          key={q}
                          className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-sm text-text/50"
                        >
                          {q}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* ── Personality Module ─────────────────────────────────── */}
            <Card
              title="Personality"
              subtitle="Big Five traits from the mini-IPIP assessment"
              expandable
              expandedContent={
                <div className="text-sm text-text/50 space-y-2">
                  <p>
                    <strong className="text-text/70">Methodology:</strong> The
                    mini-IPIP is a validated 20-item short form of the
                    International Personality Item Pool Big Five factor markers
                    (Donnellan et al., 2006).
                  </p>
                  <p>
                    <strong className="text-text/70">Scale:</strong> Each trait
                    is scored 0-100. Higher scores indicate stronger expression
                    of that trait. Scores near 50 indicate moderate expression.
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

                <div className="pt-4 border-t border-white/5">
                  <div className="flex flex-wrap gap-3">
                    <div className="px-4 py-2 bg-accent/10 border border-accent/20 rounded-xl">
                      <span className="text-xs text-accent/60 block">
                        Attachment Style
                      </span>
                      <span className="text-base font-semibold text-accent capitalize">
                        {identity.personality.attachment_style.replace(
                          "-",
                          " / ",
                        )}
                      </span>
                    </div>
                    {identity.personality.enneagram_type && (
                      <div className="px-4 py-2 bg-secondary/10 border border-secondary/20 rounded-xl">
                        <span className="text-xs text-secondary/60 block">
                          Enneagram
                        </span>
                        <span className="text-base font-semibold text-secondary">
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

            {/* ── Strengths Map ──────────────────────────────────────── */}
            {identity.strengths_map && identity.strengths_map.length > 0 && (
              <Card
                title="Strengths Map"
                subtitle="Top strengths derived from all identity systems"
              >
                <div className="flex flex-wrap gap-2">
                  {identity.strengths_map.map((strength) => (
                    <span
                      key={strength}
                      className="px-4 py-2 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/15 rounded-xl text-sm font-medium text-primary"
                    >
                      {strength}
                    </span>
                  ))}
                </div>
              </Card>
            )}

            {/* ── Coming Soon: Other Systems ─────────────────────────── */}
            <div className="pt-4">
              <h2 className="text-xl font-bold mb-4 text-text/40">
                Other Systems
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ComingSoonSection title="Healing — Ethical Healing System" />
                <ComingSoonSection title="Wealth — Generational Wealth Engine" />
                <ComingSoonSection title="Creative — Creative Forge" />
                <ComingSoonSection title="Perspective — Perspective Prism" />
              </div>
            </div>
          </div>
        ) : (
          /* Fallback when identity data is not yet populated */
          <div className="text-center py-12">
            <div className="text-4xl mb-4">📋</div>
            <h2 className="text-xl font-bold mb-2">Report Generated</h2>
            <p className="text-text/50 mb-6">
              Your report has been created but the identity layer has not been
              populated yet. This may happen when the engine pipeline is still
              being configured.
            </p>
            <pre className="card-surface p-4 text-left text-xs text-text/40 overflow-auto max-h-80 mb-6">
              {JSON.stringify(report, null, 2)}
            </pre>
          </div>
        )}

        {/* Actions */}
        <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button
            variant="ghost"
            onClick={() => {
              const apiUrl =
                process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
              window.open(
                `${apiUrl}/api/v1/reports/${reportId}/html`,
                "_blank",
              );
            }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export PDF
          </Button>
          <Button onClick={() => router.push("/")}>Back to Home</Button>
        </div>
      </div>
    </div>
  );
}
