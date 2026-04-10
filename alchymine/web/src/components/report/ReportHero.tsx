"use client";

import { useCallback, useEffect, useState } from "react";

import { generateArt, artImageUrl } from "@/lib/artApi";

interface ReportHeroProps {
  reportId: string;
  userId: string;
}

interface HeroState {
  status: "idle" | "loading" | "ready" | "placeholder" | "error";
  imageObjectUrl: string | null;
  prompt: string | null;
}

const INITIAL_STATE: HeroState = {
  status: "loading",
  imageObjectUrl: null,
  prompt: null,
};

/**
 * Fetch the protected image bytes and return an object URL.
 *
 * The image GET endpoint requires the same auth as every other API
 * call, so we cannot put the URL directly into an <img src=...>. Instead
 * we fetch the bytes with credentials and create a blob URL.
 */
async function fetchImageBlobUrl(imageId: string): Promise<string | null> {
  const url = artImageUrl(imageId);
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem("access_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(url, { headers, credentials: "include" });
  if (!res.ok) return null;
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export default function ReportHero({ reportId, userId }: ReportHeroProps) {
  const [state, setState] = useState<HeroState>(INITIAL_STATE);
  const [regenerating, setRegenerating] = useState(false);

  const loadImage = useCallback(async () => {
    setState((prev) => ({ ...prev, status: "loading" }));
    try {
      const result = await generateArt({});
      if (result === null) {
        // 204 — Gemini disabled. Render placeholder.
        setState({
          status: "placeholder",
          imageObjectUrl: null,
          prompt: null,
        });
        return;
      }
      const objectUrl = await fetchImageBlobUrl(result.image_id);
      if (objectUrl === null) {
        setState({
          status: "placeholder",
          imageObjectUrl: null,
          prompt: result.prompt,
        });
        return;
      }
      setState({
        status: "ready",
        imageObjectUrl: objectUrl,
        prompt: result.prompt,
      });
    } catch (err) {
      // Network or 5xx — fall back to the placeholder so the report
      // page never breaks because art is unavailable.
      // eslint-disable-next-line no-console
      console.warn("ReportHero generation failed:", err);
      setState({
        status: "placeholder",
        imageObjectUrl: null,
        prompt: null,
      });
    }
  }, []);

  useEffect(() => {
    void loadImage();
    // Clean up the previous blob URL when the component unmounts.
    return () => {
      setState((prev) => {
        if (prev.imageObjectUrl) URL.revokeObjectURL(prev.imageObjectUrl);
        return prev;
      });
    };
    // We intentionally re-run when reportId changes so the report page
    // can swap reports without remounting the component tree.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, userId]);

  const handleRegenerate = useCallback(async () => {
    if (regenerating) return;
    setRegenerating(true);
    if (state.imageObjectUrl) URL.revokeObjectURL(state.imageObjectUrl);
    await loadImage();
    setRegenerating(false);
  }, [loadImage, regenerating, state.imageObjectUrl]);

  // ── Loading skeleton ──────────────────────────────────────────────
  if (state.status === "loading") {
    return (
      <div
        className="w-full h-56 sm:h-72 rounded-2xl bg-gradient-to-br from-secondary/30 via-primary/20 to-accent/30 animate-pulse"
        role="status"
        aria-label="Generating personalized illustration"
      />
    );
  }

  // ── Placeholder (Gemini disabled or network error) ────────────────
  if (state.status === "placeholder" || !state.imageObjectUrl) {
    return (
      <div
        className="relative w-full h-56 sm:h-72 rounded-2xl overflow-hidden border border-white/[0.06]"
        role="img"
        aria-label="Personalized illustration placeholder"
      >
        {/* On-brand gradient using the project palette tokens */}
        <div className="absolute inset-0 bg-gradient-to-br from-secondary/50 via-primary/30 to-accent/40" />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 20% 80%, rgba(123,45,142,0.35) 0%, transparent 55%), radial-gradient(ellipse at 80% 20%, rgba(218,165,32,0.25) 0%, transparent 55%), radial-gradient(ellipse at 50% 50%, rgba(32,178,170,0.18) 0%, transparent 60%)",
          }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs font-body uppercase tracking-[0.2em] text-text/40">
            Personalized art unavailable
          </span>
        </div>
      </div>
    );
  }

  // ── Image ready ───────────────────────────────────────────────────
  return (
    <figure className="relative w-full rounded-2xl overflow-hidden border border-white/[0.06] group">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={state.imageObjectUrl}
        alt={
          state.prompt
            ? `Personalized symbolic illustration: ${state.prompt.slice(0, 120)}`
            : "Personalized symbolic illustration of your archetype and elemental energy"
        }
        className="w-full h-56 sm:h-72 object-cover"
      />

      <button
        type="button"
        onClick={handleRegenerate}
        disabled={regenerating}
        aria-label="Regenerate personalized illustration"
        className="absolute top-3 right-3 px-3 py-1.5 text-xs font-body uppercase tracking-[0.15em] rounded-full bg-bg/70 backdrop-blur border border-white/[0.08] text-text/70 hover:text-primary hover:border-primary/40 transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary/40"
      >
        {regenerating ? "Generating…" : "Regenerate"}
      </button>

      {state.prompt && (
        <figcaption className="px-4 py-2 text-[0.65rem] font-body text-text/30 bg-surface/60 truncate">
          AI-generated illustration · {state.prompt.slice(0, 96)}
          {state.prompt.length > 96 ? "…" : ""}
        </figcaption>
      )}
    </figure>
  );
}
