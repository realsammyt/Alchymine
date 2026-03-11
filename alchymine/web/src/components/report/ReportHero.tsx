"use client";

import { useEffect, useState } from "react";
import { ArtProfile, GenerateArtResponse, generateArt } from "@/lib/artApi";

// ─── Props ────────────────────────────────────────────────────────────────

interface ReportHeroProps {
  /** User profile data used to build a personalized art prompt. */
  profile?: ArtProfile;
  /** Optional explicit prompt (overrides profile-based prompt building). */
  prompt?: string;
  /** JWT access token forwarded to the API. */
  token?: string;
  /** Alt text for the generated image. */
  altText?: string;
}

// ─── Gradient placeholder ─────────────────────────────────────────────────

function HeroPlaceholder() {
  return (
    <div
      aria-hidden="true"
      className="w-full h-64 sm:h-80 rounded-2xl overflow-hidden relative"
      style={{
        background:
          "linear-gradient(135deg, #1a1208 0%, #2d1f0a 25%, #1a1a2e 50%, #0d1117 75%, #1a1208 100%)",
      }}
    >
      {/* Animated shimmer overlay */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(218,165,32,0.15) 50%, transparent 100%)",
          animation: "shimmer 3s ease-in-out infinite",
        }}
      />
      {/* Radial glow */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 50%, rgba(218,165,32,0.08) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────

function HeroSkeleton() {
  return (
    <div
      role="status"
      aria-label="Generating your personalized hero image"
      className="w-full h-64 sm:h-80 rounded-2xl overflow-hidden bg-white/[0.03] animate-pulse"
    >
      <div className="w-full h-full bg-gradient-to-br from-primary/5 to-secondary/5" />
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────

export default function ReportHero({
  profile,
  prompt,
  token,
  altText = "Personalized report hero image",
}: ReportHeroProps) {
  const [artResult, setArtResult] = useState<GenerateArtResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchImage() {
      setLoading(true);
      try {
        const result = await generateArt({ prompt, profile }, token);
        if (!cancelled) {
          setArtResult(result);
        }
      } catch {
        // Silently fall back to placeholder — art is non-critical
        if (!cancelled) {
          setArtResult(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchImage();

    return () => {
      cancelled = true;
    };
  }, [prompt, profile, token]);

  if (loading) {
    return <HeroSkeleton />;
  }

  if (!artResult) {
    return <HeroPlaceholder />;
  }

  const imageSrc = `data:${artResult.mime_type};base64,${artResult.data_b64}`;

  return (
    <div className="w-full h-64 sm:h-80 rounded-2xl overflow-hidden relative">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageSrc}
        alt={altText}
        className="w-full h-full object-cover"
      />
      {/* Subtle bottom fade for text legibility below */}
      <div
        aria-hidden="true"
        className="absolute bottom-0 left-0 right-0 h-20 pointer-events-none"
        style={{
          background: "linear-gradient(to bottom, transparent, rgba(10,10,10,0.6))",
        }}
      />
    </div>
  );
}
