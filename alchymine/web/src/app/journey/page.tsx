"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import { useAuth } from "@/lib/AuthContext";
import { getProfile, ProfileResponse, listUserReports, ReportListItem } from "@/lib/api";
import {
  generateArt,
  listGeneratedImages,
  fetchImageBlobUrl,
  GeneratedImageMetadata,
} from "@/lib/artApi";

// ── Milestone definitions ───────────────────────────────────────────

interface Milestone {
  id: string;
  label: string;
  description: string;
  /** Returns true when the milestone is complete for this profile. */
  check: (profile: ProfileResponse | null, reports: ReportListItem[]) => boolean;
}

const MILESTONES: Milestone[] = [
  {
    id: "intake",
    label: "Intake",
    description: "Completed your initial intake and assessment",
    check: (p) => !!p?.intake,
  },
  {
    id: "identity",
    label: "Identity",
    description: "Identity profile computed from your birth data",
    check: (p) => !!p?.identity,
  },
  {
    id: "healing",
    label: "Healing",
    description: "Explored ethical healing modalities",
    check: (p) => !!p?.healing,
  },
  {
    id: "wealth",
    label: "Wealth",
    description: "Mapped your generational wealth profile",
    check: (p) => !!p?.wealth,
  },
  {
    id: "creative",
    label: "Creative",
    description: "Assessed your creative development style",
    check: (p) => !!p?.creative,
  },
  {
    id: "perspective",
    label: "Perspective",
    description: "Enhanced your perspective and growth stage",
    check: (p) => !!p?.perspective,
  },
  {
    id: "synthesis",
    label: "Synthesis",
    description: "Generated your full Alchymine report",
    check: (_p, reports) => reports.some((r) => r.status === "complete"),
  },
];

// ── Types ───────────────────────────────────────────────────────────

type PageStatus =
  | { kind: "loading" }
  | { kind: "idle" }
  | { kind: "generating"; milestoneId: string }
  | { kind: "error"; message: string };

interface MilestoneImage {
  milestoneId: string;
  blobUrl: string;
}

// ── Component ───────────────────────────────────────────────────────

function JourneyBody() {
  const { user } = useAuth();
  const userId = user?.id ?? null;

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [status, setStatus] = useState<PageStatus>({ kind: "loading" });
  const [milestoneImages, setMilestoneImages] = useState<MilestoneImage[]>([]);

  // Load profile and reports
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    setStatus({ kind: "loading" });

    Promise.all([
      getProfile(userId).catch(() => null),
      listUserReports(userId, { limit: 20 }).catch(() => null),
    ]).then(([profileRes, reportsRes]) => {
      if (cancelled) return;
      setProfile(profileRes);
      setReports(reportsRes?.reports ?? []);
      setStatus({ kind: "idle" });
    });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  // Load existing generated images and try to match them to milestones
  useEffect(() => {
    let cancelled = false;
    listGeneratedImages(50, 0)
      .then(async (response) => {
        if (cancelled) return;
        const matched: MilestoneImage[] = [];
        for (const img of response.images) {
          const milestoneId = _matchImageToMilestone(img);
          if (milestoneId) {
            const blobUrl = await fetchImageBlobUrl(img.id);
            if (blobUrl && !cancelled) {
              matched.push({ milestoneId, blobUrl });
            }
          }
        }
        if (!cancelled) setMilestoneImages(matched);
      })
      .catch(() => {
        /* silent — gallery loading is best-effort */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const completedMilestones = useMemo(
    () =>
      new Set(
        MILESTONES.filter((m) => m.check(profile, reports)).map((m) => m.id),
      ),
    [profile, reports],
  );

  const imageMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const mi of milestoneImages) {
      if (!map.has(mi.milestoneId)) {
        map.set(mi.milestoneId, mi.blobUrl);
      }
    }
    return map;
  }, [milestoneImages]);

  const handleGenerateForMilestone = useCallback(
    async (milestoneId: string) => {
      setStatus({ kind: "generating", milestoneId });
      try {
        const result = await generateArt({
          style_preset: "mystical",
          user_prompt_extension: `Journey milestone illustration for the "${milestoneId}" stage of personal transformation`,
        });
        if (result === null) {
          setStatus({
            kind: "error",
            message: "Image generation is offline. Try later.",
          });
          return;
        }
        const blobUrl = await fetchImageBlobUrl(result.image_id);
        if (blobUrl) {
          setMilestoneImages((prev) => [
            ...prev,
            { milestoneId, blobUrl },
          ]);
        }
        setStatus({ kind: "idle" });
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Generation failed";
        setStatus({ kind: "error", message });
      }
    },
    [],
  );

  const progressPct =
    MILESTONES.length > 0
      ? Math.round((completedMilestones.size / MILESTONES.length) * 100)
      : 0;

  return (
    <main
      id="main-content"
      className="grain-overlay bg-atmosphere min-h-screen px-4 sm:px-6 lg:px-8 py-8"
    >
      <div className="max-w-4xl mx-auto">
        <header className="mb-10">
          <h1 className="font-display text-display-md font-light text-gradient-purple mb-3">
            Your Journey
          </h1>
          <hr className="rule-gold mb-4" aria-hidden="true" />
          <p className="font-body text-text/50 text-base max-w-2xl">
            A visual timeline of your transformation path. Each milestone
            unlocks as you progress through the five Alchymine systems.
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 mt-4 text-sm font-body text-secondary hover:text-secondary-light focus:outline-none focus:underline"
          >
            &larr; Back to Dashboard
          </Link>
        </header>

        {/* Progress bar */}
        <section className="mb-10" aria-label="Journey progress">
          <div className="flex items-center justify-between mb-2">
            <span className="font-body text-sm text-text/60">Progress</span>
            <span
              className="font-mono text-sm text-primary"
              aria-live="polite"
            >
              {progressPct}%
            </span>
          </div>
          <div
            className="w-full h-3 bg-surface rounded-full overflow-hidden border border-white/[0.06]"
            role="progressbar"
            aria-valuenow={progressPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Journey ${progressPct}% complete`}
          >
            <div
              className="h-full bg-gradient-to-r from-primary via-secondary to-accent transition-all duration-700 ease-out rounded-full"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </section>

        {status.kind === "error" && (
          <div
            role="alert"
            className="mb-6 px-4 py-3 rounded-lg bg-red-900/20 border border-red-700/30 text-red-200 text-sm font-body"
          >
            {status.message}
          </div>
        )}

        {/* Timeline */}
        <section aria-label="Transformation timeline">
          <ol className="relative border-l-2 border-white/[0.08] ml-4 space-y-8">
            {MILESTONES.map((milestone) => {
              const completed = completedMilestones.has(milestone.id);
              const blobUrl = imageMap.get(milestone.id);
              const isGenerating =
                status.kind === "generating" &&
                status.milestoneId === milestone.id;

              return (
                <li key={milestone.id} className="pl-8 relative">
                  {/* Node marker */}
                  <div
                    className={`absolute -left-[11px] top-1 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      completed
                        ? "bg-primary border-primary"
                        : "bg-surface border-white/20"
                    }`}
                    aria-hidden="true"
                  >
                    {completed && (
                      <svg
                        className="w-3 h-3 text-bg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                  </div>

                  <div
                    className={`rounded-xl border p-4 transition-colors ${
                      completed
                        ? "border-primary/20 bg-primary/5"
                        : "border-white/[0.06] bg-surface"
                    }`}
                  >
                    <div className="flex items-center gap-3 mb-1">
                      <h3
                        className={`font-display text-lg font-medium ${
                          completed ? "text-primary" : "text-text/70"
                        }`}
                      >
                        {milestone.label}
                      </h3>
                      {completed && (
                        <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-[10px] font-body uppercase tracking-wider">
                          Complete
                        </span>
                      )}
                    </div>
                    <p className="font-body text-sm text-text/50 mb-3">
                      {milestone.description}
                    </p>

                    {/* Milestone illustration */}
                    {blobUrl && (
                      <div className="mb-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={blobUrl}
                          alt={`Illustration for ${milestone.label} milestone`}
                          className="w-full max-h-48 object-cover rounded-lg"
                        />
                      </div>
                    )}

                    {/* Generate illustration button */}
                    {completed && !blobUrl && (
                      <button
                        type="button"
                        onClick={() =>
                          handleGenerateForMilestone(milestone.id)
                        }
                        disabled={status.kind === "generating"}
                        className="px-4 py-2 min-h-[44px] text-xs font-body font-medium rounded-lg bg-secondary/20 text-secondary border border-secondary/30 hover:bg-secondary/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-secondary/60"
                        aria-label={`Generate illustration for ${milestone.label} milestone`}
                      >
                        {isGenerating
                          ? "Generating..."
                          : "Generate Milestone Art"}
                      </button>
                    )}

                    {isGenerating && (
                      <div
                        role="status"
                        aria-label="Generating milestone illustration"
                        className="mt-2 w-full h-32 rounded-lg bg-gradient-to-br from-secondary/30 via-primary/20 to-accent/30 animate-pulse"
                      />
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </section>
      </div>
    </main>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────

/**
 * Heuristic: try to match a generated image's prompt text to a milestone id.
 * Returns the milestone id if a keyword match is found, or null.
 */
function _matchImageToMilestone(
  img: GeneratedImageMetadata,
): string | null {
  const lower = img.prompt.toLowerCase();
  for (const m of MILESTONES) {
    if (lower.includes(`"${m.id}"`) || lower.includes(`'${m.id}'`)) {
      return m.id;
    }
  }
  return null;
}

// ── Default export ──────────────────────────────────────────────────

export default function JourneyPage() {
  return (
    <ProtectedRoute>
      <JourneyBody />
    </ProtectedRoute>
  );
}
