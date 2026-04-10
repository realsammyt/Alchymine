"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useAuth } from "@/lib/AuthContext";
import { getProfile, ProfileResponse } from "@/lib/api";
import {
  getBrandPalette,
  generateBrandLogo,
  fetchImageBlobUrl,
  BrandPalette,
} from "@/lib/artApi";

// ── Typography recommendations ──────────────────────────────────────

interface TypographyRec {
  category: string;
  font: string;
  weight: string;
  usage: string;
}

const ELEMENT_TYPOGRAPHY: Record<string, TypographyRec[]> = {
  fire: [
    {
      category: "Display",
      font: "Playfair Display",
      weight: "Bold",
      usage: "Headlines and hero text",
    },
    {
      category: "Body",
      font: "Source Sans Pro",
      weight: "Regular",
      usage: "Body copy and paragraphs",
    },
    {
      category: "Accent",
      font: "Oswald",
      weight: "Medium",
      usage: "Labels and CTAs",
    },
  ],
  earth: [
    {
      category: "Display",
      font: "Lora",
      weight: "Bold",
      usage: "Headlines and hero text",
    },
    {
      category: "Body",
      font: "Open Sans",
      weight: "Regular",
      usage: "Body copy and paragraphs",
    },
    {
      category: "Accent",
      font: "Merriweather",
      weight: "Italic",
      usage: "Pull quotes and emphasis",
    },
  ],
  air: [
    {
      category: "Display",
      font: "Inter",
      weight: "Light",
      usage: "Headlines and hero text",
    },
    {
      category: "Body",
      font: "DM Sans",
      weight: "Regular",
      usage: "Body copy and paragraphs",
    },
    {
      category: "Accent",
      font: "Space Mono",
      weight: "Regular",
      usage: "Data and labels",
    },
  ],
  water: [
    {
      category: "Display",
      font: "Cormorant Garamond",
      weight: "SemiBold",
      usage: "Headlines and hero text",
    },
    {
      category: "Body",
      font: "Nunito",
      weight: "Regular",
      usage: "Body copy and paragraphs",
    },
    {
      category: "Accent",
      font: "Josefin Sans",
      weight: "Light",
      usage: "Decorative and navigation",
    },
  ],
};

// ── Pattern recommendations ─────────────────────────────────────────

const ARCHETYPE_PATTERNS: Record<string, string[]> = {
  sage: ["Sacred geometry", "Mandala motifs", "Concentric circles"],
  creator: ["Tessellated shapes", "Exploded wireframes", "Colour blocks"],
  explorer: ["Topographic lines", "Star charts", "Wave patterns"],
  mystic: ["Moon phases", "Alchemical symbols", "Spiral forms"],
  ruler: ["Grid systems", "Crown motifs", "Shield geometry"],
  lover: ["Intertwined vines", "Flowing curves", "Petal gradients"],
  hero: ["Rising arrows", "Mountain silhouettes", "Sun rays"],
  caregiver: ["Leaf veins", "Nest patterns", "Gentle arcs"],
  jester: ["Kaleidoscope", "Confetti scatter", "Zigzag lines"],
  innocent: ["Dot patterns", "Soft clouds", "Daisy chains"],
  rebel: ["Shattered glass", "Lightning bolts", "Contrast blocks"],
  everyman: ["Woven textures", "Brick patterns", "Path lines"],
};

// ── Element detection ───────────────────────────────────────────────

const SIGN_ELEMENT: Record<string, string> = {
  aries: "fire",
  leo: "fire",
  sagittarius: "fire",
  taurus: "earth",
  virgo: "earth",
  capricorn: "earth",
  gemini: "air",
  libra: "air",
  aquarius: "air",
  cancer: "water",
  scorpio: "water",
  pisces: "water",
};

function getElement(profile: ProfileResponse | null): string {
  const identity = profile?.identity as Record<string, unknown> | null;
  const astrology = identity?.astrology as Record<string, unknown> | null;
  const sunSign = (astrology?.sun_sign as string) ?? "";
  return SIGN_ELEMENT[sunSign.toLowerCase()] ?? "water";
}

function getArchetype(profile: ProfileResponse | null): string {
  const identity = profile?.identity as Record<string, unknown> | null;
  const archetype = identity?.archetype as Record<string, unknown> | null;
  return ((archetype?.primary as string) ?? "").toLowerCase();
}

// ── Types ───────────────────────────────────────────────────────────

type PageStatus =
  | { kind: "loading" }
  | { kind: "idle" }
  | { kind: "generating-logo" }
  | { kind: "offline" }
  | { kind: "error"; message: string };

// ── Component ───────────────────────────────────────────────────────

function BrandBody() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [palette, setPalette] = useState<BrandPalette | null>(null);
  const [logoUrl, setLogoUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<PageStatus>({ kind: "loading" });

  // Load profile and palette
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setStatus({ kind: "loading" });

    Promise.all([
      getProfile(userId).catch(() => null),
      getBrandPalette().catch(() => null),
    ]).then(([profileRes, paletteRes]) => {
      if (cancelled) return;
      setProfile(profileRes);
      setPalette(paletteRes);
      setStatus({ kind: "idle" });
    });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  const element = getElement(profile);
  const archetype = getArchetype(profile);
  const typography = ELEMENT_TYPOGRAPHY[element] ?? ELEMENT_TYPOGRAPHY.water;
  const patterns = ARCHETYPE_PATTERNS[archetype] ?? [
    "Abstract geometric forms",
    "Flowing organic lines",
    "Balanced symmetry",
  ];

  const handleGenerateLogo = useCallback(async () => {
    setStatus({ kind: "generating-logo" });
    try {
      const result = await generateBrandLogo();
      if (result === null) {
        setStatus({ kind: "offline" });
        return;
      }
      const blobUrl = await fetchImageBlobUrl(result.image_id);
      if (blobUrl) setLogoUrl(blobUrl);
      setStatus({ kind: "idle" });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Logo generation failed";
      setStatus({ kind: "error", message });
    }
  }, []);

  return (
    <main
      id="main-content"
      className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="max-w-4xl mx-auto">
        <header className="mb-10">
          <h1 className="font-display text-display-md font-light text-gradient-purple mb-3">
            Personal Brand
          </h1>
          <hr className="rule-gold mb-4" aria-hidden="true" />
          <p className="font-body text-text/50 text-base max-w-2xl">
            Your brand identity, derived from your archetypes, numerology,
            and elemental energy. Every element is deterministic and unique
            to you.
          </p>
          <Link
            href="/creative"
            className="inline-flex items-center gap-2 mt-4 text-sm font-body text-secondary hover:text-secondary-light focus:outline-none focus:underline"
          >
            &larr; Back to Creative Development
          </Link>
        </header>

        {status.kind === "loading" && (
          <div
            role="status"
            aria-label="Loading brand profile"
            className="space-y-6"
          >
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-32 rounded-xl bg-gradient-to-br from-secondary/20 via-primary/15 to-accent/20 animate-pulse"
              />
            ))}
          </div>
        )}

        {status.kind === "offline" && (
          <div
            role="status"
            className="mb-6 px-4 py-3 rounded-lg bg-yellow-900/20 border border-yellow-700/30 text-yellow-200 text-sm font-body"
          >
            Logo generation is offline. Try later.
          </div>
        )}

        {status.kind === "error" && (
          <div
            role="alert"
            className="mb-6 px-4 py-3 rounded-lg bg-red-900/20 border border-red-700/30 text-red-200 text-sm font-body"
          >
            {status.message}
          </div>
        )}

        {status.kind !== "loading" && (
          <div className="space-y-8">
            {/* Logo Section */}
            <section
              aria-labelledby="logo-heading"
              className="rounded-xl border border-white/[0.06] bg-surface p-6"
            >
              <h2
                id="logo-heading"
                className="font-display text-xl font-medium text-text mb-4"
              >
                Brand Mark
              </h2>
              <p className="font-body text-sm text-text/50 mb-4">
                A symbolic logo derived from your archetype and elemental
                energy. Generated by AI, unique to your profile.
              </p>
              {logoUrl ? (
                <div className="flex justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={logoUrl}
                    alt="Your personal brand logo mark"
                    className="w-48 h-48 object-contain rounded-xl border border-white/[0.08] bg-bg p-4"
                  />
                </div>
              ) : (
                <div className="flex justify-center">
                  <button
                    type="button"
                    onClick={handleGenerateLogo}
                    disabled={status.kind === "generating-logo"}
                    className="px-6 py-3 min-h-[44px] bg-gradient-to-r from-secondary-dark via-secondary to-secondary-light text-white font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none"
                    aria-label="Generate your personal brand logo"
                  >
                    {status.kind === "generating-logo"
                      ? "Generating..."
                      : "Generate Logo"}
                  </button>
                </div>
              )}
              {status.kind === "generating-logo" && (
                <div
                  role="status"
                  aria-label="Generating logo"
                  className="mt-4 w-48 h-48 mx-auto rounded-xl bg-gradient-to-br from-secondary/30 via-primary/20 to-accent/30 animate-pulse"
                />
              )}
            </section>

            {/* Colour Palette Section */}
            <section
              aria-labelledby="palette-heading"
              className="rounded-xl border border-white/[0.06] bg-surface p-6"
            >
              <h2
                id="palette-heading"
                className="font-display text-xl font-medium text-text mb-4"
              >
                Colour Palette
              </h2>
              <p className="font-body text-sm text-text/50 mb-4">
                Derived from your zodiac element ({element}) and archetype
                ({archetype || "wanderer"}). Use these colours across your
                personal brand materials.
              </p>
              {palette ? (
                <div
                  className="grid grid-cols-2 sm:grid-cols-4 gap-4"
                  role="list"
                  aria-label="Brand colour palette"
                >
                  {(
                    ["primary", "secondary", "accent", "neutral"] as const
                  ).map((key) => {
                    const color = palette[key];
                    return (
                      <div
                        key={key}
                        role="listitem"
                        className="text-center"
                      >
                        <div
                          className="w-full aspect-square rounded-xl border border-white/[0.08] mb-2"
                          style={{ backgroundColor: color.hex }}
                          aria-hidden="true"
                        />
                        <p className="font-body text-sm font-medium text-text">
                          {color.name}
                        </p>
                        <p className="font-mono text-xs text-text/40 mt-0.5">
                          {color.hex}
                        </p>
                        <p className="font-body text-[10px] text-text/30 uppercase tracking-wider mt-0.5">
                          {key}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="font-body text-sm text-text/40">
                  Complete your intake to unlock your colour palette.
                </p>
              )}
            </section>

            {/* Typography Section */}
            <section
              aria-labelledby="typography-heading"
              className="rounded-xl border border-white/[0.06] bg-surface p-6"
            >
              <h2
                id="typography-heading"
                className="font-display text-xl font-medium text-text mb-4"
              >
                Typography
              </h2>
              <p className="font-body text-sm text-text/50 mb-4">
                Font recommendations matched to your elemental energy.
              </p>
              <div className="space-y-4">
                {typography.map((rec) => (
                  <div
                    key={rec.category}
                    className="flex items-start gap-4 p-3 rounded-lg bg-bg/40 border border-white/[0.04]"
                  >
                    <div className="min-w-[72px]">
                      <span className="px-2 py-0.5 rounded-full bg-primary/15 text-primary text-[10px] font-body uppercase tracking-wider">
                        {rec.category}
                      </span>
                    </div>
                    <div>
                      <p className="font-body text-sm font-medium text-text">
                        {rec.font}
                      </p>
                      <p className="font-body text-xs text-text/40">
                        {rec.weight} &middot; {rec.usage}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Pattern Recommendations Section */}
            <section
              aria-labelledby="patterns-heading"
              className="rounded-xl border border-white/[0.06] bg-surface p-6"
            >
              <h2
                id="patterns-heading"
                className="font-display text-xl font-medium text-text mb-4"
              >
                Pattern Language
              </h2>
              <p className="font-body text-sm text-text/50 mb-4">
                Visual patterns aligned with your archetype (
                {archetype || "wanderer"}).
              </p>
              <ul className="space-y-2" role="list">
                {patterns.map((pattern) => (
                  <li
                    key={pattern}
                    className="flex items-center gap-3 p-3 rounded-lg bg-bg/40 border border-white/[0.04]"
                  >
                    <span
                      className="w-2 h-2 rounded-full bg-accent flex-shrink-0"
                      aria-hidden="true"
                    />
                    <span className="font-body text-sm text-text/70">
                      {pattern}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}
      </div>
    </main>
  );
}

export default function BrandPage() {
  return (
    <ProtectedRoute>
      <BrandBody />
    </ProtectedRoute>
  );
}
