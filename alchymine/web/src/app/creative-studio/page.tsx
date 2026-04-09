"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import StylePresetPicker, {
  CreativeProfile,
} from "@/components/creative/StylePresetPicker";
import ArtGallery, { GalleryImage } from "@/components/creative/ArtGallery";
import {
  generateArt,
  listGeneratedImages,
  deleteGeneratedImage,
} from "@/lib/artApi";
import { getProfile, ProfileResponse } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

const PROMPT_MAX_LENGTH = 500;

type StudioStatus =
  | { kind: "idle" }
  | { kind: "loading-gallery" }
  | { kind: "generating" }
  | { kind: "offline" }
  | { kind: "error"; message: string };

function toGalleryImage(meta: {
  id: string;
  prompt: string;
  style_preset: string | null;
  created_at: string;
}): GalleryImage {
  return {
    id: meta.id,
    prompt: meta.prompt,
    stylePreset: meta.style_preset,
    createdAt: meta.created_at,
  };
}

function extractCreativeProfile(
  profile: ProfileResponse | null,
): CreativeProfile | null {
  if (!profile || !profile.creative) return null;
  const creative = profile.creative as Record<string, unknown>;
  const orientation =
    typeof creative.creative_orientation === "string"
      ? creative.creative_orientation
      : null;
  const style =
    typeof creative.creative_style === "string" ? creative.creative_style : null;
  if (!orientation && !style) return null;
  return {
    creative_orientation: orientation,
    creative_style: style,
  };
}

function StudioBody() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [prompt, setPrompt] = useState("");
  const [preset, setPreset] = useState<string | null>(null);
  const [enhanceWithProfile, setEnhanceWithProfile] = useState(true);
  const [gallery, setGallery] = useState<GalleryImage[]>([]);
  const [status, setStatus] = useState<StudioStatus>({ kind: "loading-gallery" });
  const [creativeProfile, setCreativeProfile] =
    useState<CreativeProfile | null>(null);

  // Load existing gallery on mount.
  useEffect(() => {
    let cancelled = false;
    setStatus({ kind: "loading-gallery" });
    listGeneratedImages(20, 0)
      .then((response) => {
        if (cancelled) return;
        setGallery(response.images.map(toGalleryImage));
        setStatus({ kind: "idle" });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Failed to load gallery";
        setStatus({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load creative profile on mount for preset suggestion (best-effort).
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    getProfile(userId)
      .then((profile) => {
        if (cancelled) return;
        setCreativeProfile(extractCreativeProfile(profile));
      })
      .catch(() => {
        /* silent — profile is optional for preset suggestion */
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  const charactersRemaining = useMemo(
    () => PROMPT_MAX_LENGTH - prompt.length,
    [prompt.length],
  );

  const canGenerate =
    prompt.trim().length > 0 &&
    status.kind !== "generating" &&
    status.kind !== "offline";

  const handleGenerate = useCallback(async () => {
    if (!canGenerate) return;
    setStatus({ kind: "generating" });
    try {
      const result = await generateArt({
        style_preset: preset,
        user_prompt_extension: enhanceWithProfile ? prompt.trim() : prompt.trim(),
      });
      if (result === null) {
        // 204 — Gemini unavailable. Preserve prompt, surface message.
        setStatus({ kind: "offline" });
        return;
      }
      const newImage: GalleryImage = {
        id: result.image_id,
        prompt: result.prompt,
        stylePreset: preset,
        createdAt: new Date().toISOString(),
      };
      setGallery((prev) => [newImage, ...prev]);
      setStatus({ kind: "idle" });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Generation failed";
      setStatus({ kind: "error", message });
    }
  }, [canGenerate, preset, prompt, enhanceWithProfile]);

  const handleDelete = useCallback(async (imageId: string) => {
    try {
      const ok = await deleteGeneratedImage(imageId);
      if (ok) {
        setGallery((prev) => prev.filter((img) => img.id !== imageId));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Delete failed";
      setStatus({ kind: "error", message });
    }
  }, []);

  const promptId = "studio-prompt";
  const enhanceId = "studio-enhance";

  return (
    <main
      id="main-content"
      className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="max-w-5xl mx-auto">
        <header className="mb-10">
          <h1 className="font-display text-display-md font-light text-gradient-purple mb-3">
            Creative Studio
          </h1>
          <hr className="rule-gold mb-4" aria-hidden="true" />
          <p className="font-body text-text/50 text-base max-w-2xl">
            Generate personalized symbolic art from your creative profile.
            Describe what you want to see, pick a style, and Alchymine will
            blend it with your archetype and elemental energy.
          </p>
          <Link
            href="/creative"
            className="inline-flex items-center gap-2 mt-4 text-sm font-body text-secondary hover:text-secondary-light focus:outline-none focus:underline"
          >
            &larr; Back to Creative Development
          </Link>
        </header>

        {status.kind === "offline" && (
          <div
            role="status"
            className="mb-6 px-4 py-3 rounded-lg bg-yellow-900/20 border border-yellow-700/30 text-yellow-200 text-sm font-body"
          >
            Image generation is offline. Try later.
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

        <section className="mb-10 space-y-6">
          <div>
            <label
              htmlFor={promptId}
              className="block text-sm font-body text-text/70 mb-2"
            >
              Your vision
            </label>
            <textarea
              id={promptId}
              value={prompt}
              onChange={(event) => {
                const next = event.target.value.slice(0, PROMPT_MAX_LENGTH);
                setPrompt(next);
              }}
              placeholder="Describe the image you want to create — a mood, a symbol, a setting…"
              rows={4}
              maxLength={PROMPT_MAX_LENGTH}
              className="w-full bg-surface border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/30 focus:outline-none focus:border-primary/50 resize-none"
            />
            <div className="mt-1 flex items-center justify-between">
              <label
                htmlFor={enhanceId}
                className="flex items-center gap-2 text-xs font-body text-text/60 cursor-pointer"
              >
                <input
                  id={enhanceId}
                  type="checkbox"
                  checked={enhanceWithProfile}
                  onChange={(event) =>
                    setEnhanceWithProfile(event.target.checked)
                  }
                  className="w-4 h-4 accent-primary"
                />
                Enhance with your profile
              </label>
              <span
                className={`text-xs font-mono ${
                  charactersRemaining < 50 ? "text-primary/80" : "text-text/40"
                }`}
                aria-live="polite"
              >
                {charactersRemaining} / {PROMPT_MAX_LENGTH}
              </span>
            </div>
          </div>

          <div>
            <p className="block text-sm font-body text-text/70 mb-2">
              Style preset
            </p>
            <StylePresetPicker
              selected={preset}
              onSelect={setPreset}
              creativeProfile={creativeProfile}
            />
          </div>

          <div>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!canGenerate}
              className="px-6 py-3 min-h-[44px] bg-gradient-to-r from-secondary-dark via-secondary to-secondary-light text-white font-body font-medium rounded-xl text-sm transition-all duration-300 hover:shadow-[0_0_20px_rgba(123,45,142,0.3)] hover:scale-[1.02] active:scale-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-none"
            >
              {status.kind === "generating"
                ? "Generating…"
                : "Generate Image"}
            </button>
          </div>

          {status.kind === "generating" && (
            <div
              role="status"
              aria-label="Generating image"
              className="w-full h-56 sm:h-72 rounded-2xl bg-gradient-to-br from-secondary/30 via-primary/20 to-accent/30 animate-pulse"
            />
          )}
        </section>

        <section aria-labelledby="gallery-heading">
          <h2
            id="gallery-heading"
            className="font-display text-xl font-light text-text mb-4"
          >
            Your Gallery
          </h2>
          <hr className="rule-gold mb-4" aria-hidden="true" />
          {status.kind === "loading-gallery" ? (
            <div
              role="status"
              aria-label="Loading gallery"
              className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="aspect-video rounded-xl bg-gradient-to-br from-secondary/20 via-primary/15 to-accent/20 animate-pulse"
                />
              ))}
            </div>
          ) : (
            <ArtGallery images={gallery} onDelete={handleDelete} />
          )}
        </section>
      </div>
    </main>
  );
}

export default function CreativeStudioPage() {
  return (
    <ProtectedRoute>
      <StudioBody />
    </ProtectedRoute>
  );
}
