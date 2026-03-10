"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createJournalEntry } from "@/lib/api";
import type { ProjectResponse } from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: "bg-accent/10 text-accent/80",
  intermediate: "bg-primary/10 text-primary/80",
  advanced: "bg-secondary/10 text-secondary/80",
};

const TYPE_ICONS: Record<string, string> = {
  solo: "\u{1F464}",
  collaborative: "\u{1F465}",
  challenge: "\u{26A1}",
};

function getDifficultyColor(level: string): string {
  return DIFFICULTY_COLORS[level.toLowerCase()] ?? "bg-white/5 text-text/40";
}

function getTypeIcon(type: string): string {
  return TYPE_ICONS[type.toLowerCase()] ?? "\u{1F4DD}";
}

// ── Project Card ───────────────────────────────────────────────────

interface ProjectCardProps {
  project: ProjectResponse;
  onStart: (project: ProjectResponse) => Promise<void>;
}

function ProjectCard({ project, onStart }: ProjectCardProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );

  const handleStart = useCallback(async () => {
    setStatus("loading");
    try {
      await onStart(project);
      setStatus("done");
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  }, [project, onStart]);

  return (
    <div className="card-surface-elevated p-5 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-2 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-lg flex-shrink-0" aria-hidden="true">
            {getTypeIcon(project.type)}
          </span>
          <h3 className="font-display text-sm font-medium text-text leading-snug">
            {project.title}
          </h3>
        </div>
        <span className="px-2 py-0.5 bg-secondary/10 text-secondary/60 text-[10px] font-medium rounded-full capitalize flex-shrink-0">
          {project.type}
        </span>
      </div>

      {/* Description */}
      <p className="font-body text-sm text-text/50 leading-relaxed mb-4 flex-1">
        {project.description}
      </p>

      {/* Meta tags */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span
          className={`px-2 py-0.5 text-[10px] rounded-full capitalize font-medium ${getDifficultyColor(project.skill_level)}`}
        >
          {project.skill_level}
        </span>
        <span className="px-2 py-0.5 bg-accent/10 text-accent/70 text-[10px] rounded-full capitalize">
          {project.medium}
        </span>
      </div>

      {/* Start button */}
      <button
        onClick={handleStart}
        disabled={status === "loading" || status === "done"}
        className={`w-full py-2.5 rounded-xl font-body text-sm font-medium transition-all duration-200 min-h-[44px] ${
          status === "done"
            ? "bg-accent/20 text-accent cursor-default"
            : status === "error"
              ? "bg-red-500/20 text-red-400"
              : status === "loading"
                ? "bg-secondary/20 text-secondary/50 cursor-wait"
                : "bg-secondary/15 text-secondary hover:bg-secondary/25 hover:shadow-[0_0_12px_rgba(123,45,142,0.2)]"
        }`}
        aria-label={
          status === "done"
            ? `${project.title} project started`
            : `Start project: ${project.title}`
        }
      >
        {status === "loading"
          ? "Creating entry..."
          : status === "done"
            ? "\u2713 Project started"
            : status === "error"
              ? "Try again"
              : "Start Project"}
      </button>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────

interface CreativeProjectsProps {
  projects: ProjectResponse[];
  orientation?: string;
}

export default function CreativeProjects({
  projects,
  orientation,
}: CreativeProjectsProps) {
  const router = useRouter();
  const handleStartProject = useCallback(
    async (project: ProjectResponse) => {
      const entry = await createJournalEntry({
        system: "creative",
        entry_type: "project_start",
        title: `Started: ${project.title}`,
        content: `Beginning the creative project "${project.title}".\n\nDescription: ${project.description}\n\nMedium: ${project.medium}\nSkill level: ${project.skill_level}\nType: ${project.type}`,
        tags: ["creative", "project", project.medium, project.type],
        mood_score: null,
      });
      router.push(`/journal?highlight=${entry.id}`);
    },
    [router],
  );

  if (projects.length === 0) {
    return (
      <div
        data-testid="creative-projects"
        className="text-center py-8 font-body text-text/40 text-sm"
      >
        No projects available yet. Complete your creative profile to receive
        personalized recommendations.
      </div>
    );
  }

  return (
    <div data-testid="creative-projects">
      {orientation && (
        <p className="font-body text-xs text-text/40 mb-4 italic">
          Orientation: {orientation}
        </p>
      )}
      <div className="grid sm:grid-cols-3 gap-4">
        {projects.map((project) => (
          <ProjectCard
            key={project.title}
            project={project}
            onStart={handleStartProject}
          />
        ))}
      </div>
    </div>
  );
}
