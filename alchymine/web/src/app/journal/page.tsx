"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  createJournalEntry,
  getJournalEntries,
  getJournalStats,
  JournalEntry,
  JournalStatsResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import {
  MotionReveal,
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

const SYSTEMS = [
  "intelligence",
  "healing",
  "wealth",
  "creative",
  "perspective",
];

const ENTRY_TYPES = [
  "reflection",
  "insight",
  "gratitude",
  "intention",
  "freeform",
];

// Maps each system to a design-system color token set
type SystemColorKey =
  | "intelligence"
  | "healing"
  | "wealth"
  | "creative"
  | "perspective";

const SYSTEM_COLORS: Record<
  SystemColorKey,
  {
    border: string;
    badge: string;
    text: string;
    dot: string;
  }
> = {
  intelligence: {
    border: "border-l-accent",
    badge: "bg-accent/10 text-accent",
    text: "text-accent",
    dot: "bg-accent",
  },
  healing: {
    border: "border-l-primary",
    badge: "bg-primary/10 text-primary",
    text: "text-primary",
    dot: "bg-primary",
  },
  wealth: {
    border: "border-l-primary",
    badge: "bg-primary/10 text-primary-light",
    text: "text-primary-light",
    dot: "bg-primary-light",
  },
  creative: {
    border: "border-l-secondary-light",
    badge: "bg-secondary/10 text-secondary-light",
    text: "text-secondary-light",
    dot: "bg-secondary-light",
  },
  perspective: {
    border: "border-l-accent-light",
    badge: "bg-accent/10 text-accent-light",
    text: "text-accent-light",
    dot: "bg-accent-light",
  },
};

function getSystemColors(system: string) {
  return (
    SYSTEM_COLORS[system as SystemColorKey] ?? {
      border: "border-l-white/20",
      badge: "bg-white/[0.06] text-text/50",
      text: "text-text/50",
      dot: "bg-white/30",
    }
  );
}

function moodEmoji(score: number | null): string {
  if (score === null) return "";
  if (score >= 8) return "😊";
  if (score >= 6) return "🙂";
  if (score >= 4) return "😐";
  if (score >= 2) return "😔";
  return "😢";
}

// Mood score maps to a badge color token for non-color-only semantics
function moodLabel(score: number | null): string {
  if (score === null) return "";
  if (score >= 8) return "Positive";
  if (score >= 6) return "Good";
  if (score >= 4) return "Neutral";
  if (score >= 2) return "Low";
  return "Difficult";
}

export default function JournalPage() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [stats, setStats] = useState<JournalStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterSystem, setFilterSystem] = useState<string>("");
  const [filterType, setFilterType] = useState<string>("");

  // New entry form
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formContent, setFormContent] = useState("");
  const [formSystem, setFormSystem] = useState("intelligence");
  const [formType, setFormType] = useState("reflection");
  const [formMood, setFormMood] = useState<number>(5);
  const [formTags, setFormTags] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Selected entry detail
  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);

  // Modal close button ref for focus management
  const modalCloseRef = useRef<HTMLButtonElement>(null);

  const fetchEntries = useCallback(async () => {
    if (!user?.id) return;
    try {
      setLoading(true);
      const [journalData, statsData] = await Promise.all([
        getJournalEntries(user.id, {
          system: filterSystem || undefined,
          entryType: filterType || undefined,
        }),
        getJournalStats(user.id),
      ]);
      setEntries(journalData.entries);
      setStats(statsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load journal");
    } finally {
      setLoading(false);
    }
  }, [filterSystem, filterType, user?.id]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  // Move focus to modal close button when modal opens
  useEffect(() => {
    if (selectedEntry) {
      modalCloseRef.current?.focus();
    }
  }, [selectedEntry]);

  // Close modal on Escape key
  useEffect(() => {
    if (!selectedEntry) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelectedEntry(null);
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [selectedEntry]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formContent.trim() || !user?.id) return;

    setSubmitting(true);
    try {
      await createJournalEntry({
        user_id: user.id,
        title: formTitle.trim(),
        content: formContent.trim(),
        system: formSystem,
        entry_type: formType,
        mood_score: formMood,
        tags: formTags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setFormTitle("");
      setFormContent("");
      setFormTags("");
      setFormMood(5);
      setShowForm(false);
      await fetchEntries();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create entry");
    } finally {
      setSubmitting(false);
    }
  };

  if (!user) {
    return null;
  }

  const inputClass =
    "w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text placeholder:text-text/25 focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/20 focus:bg-white/[0.04] transition-all duration-300";

  const selectClass =
    "w-full bg-white/[0.03] border border-white/[0.08] rounded-xl px-4 py-3 text-sm font-body text-text focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/20 transition-all duration-300 appearance-none";

  const labelClass = "block text-xs font-body font-medium text-text/50 mb-1.5";

  return (
    <ProtectedRoute>
      <main id="main-content" className="grain-overlay min-h-screen bg-bg">
        <div className="bg-atmosphere min-h-screen">
          <div className="w-full px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto py-10 sm:py-14">
            {/* ── Page header ──────────────────────────────────────────── */}
            <MotionReveal delay={0.05}>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                <div>
                  <h1 className="section-heading-sm text-gradient-gold">
                    Journal
                  </h1>
                  <p className="text-sm font-body text-text/35 mt-1">
                    Your reflection practice
                  </p>
                </div>
                <button
                  onClick={() => setShowForm(!showForm)}
                  aria-expanded={showForm}
                  aria-controls="new-entry-form"
                  className="touch-target inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98] self-start sm:self-auto"
                >
                  {showForm ? (
                    <>
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
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                      Cancel
                    </>
                  ) : (
                    <>
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
                        <path d="M12 5v14" />
                        <path d="M5 12h14" />
                      </svg>
                      New Entry
                    </>
                  )}
                </button>
              </div>
            </MotionReveal>

            <hr className="rule-gold mb-8" />

            {/* ── Stats bar ────────────────────────────────────────────── */}
            {stats && (
              <MotionReveal delay={0.1}>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
                  <StatCard
                    label="Total Entries"
                    value={stats.total_entries}
                    accent="primary"
                  />
                  <StatCard
                    label="Streak"
                    value={`${stats.streak_days}d`}
                    accent="accent"
                  />
                  <StatCard
                    label="Avg Mood"
                    value={
                      stats.average_mood !== null
                        ? `${stats.average_mood.toFixed(1)} ${moodEmoji(stats.average_mood)}`
                        : "—"
                    }
                    accent="secondary"
                  />
                  <StatCard
                    label="Tags Used"
                    value={stats.tags_used.length}
                    accent="primary"
                  />
                </div>
              </MotionReveal>
            )}

            {/* ── Filters ──────────────────────────────────────────────── */}
            <MotionReveal delay={0.15}>
              <div className="flex flex-col sm:flex-row gap-3 mb-8">
                <div className="flex-1">
                  <label htmlFor="filter-system" className={labelClass}>
                    Filter by system
                  </label>
                  <div className="relative">
                    <select
                      id="filter-system"
                      value={filterSystem}
                      onChange={(e) => setFilterSystem(e.target.value)}
                      className={selectClass}
                    >
                      <option value="">All Systems</option>
                      {SYSTEMS.map((s) => (
                        <option key={s} value={s}>
                          {s.charAt(0).toUpperCase() + s.slice(1)}
                        </option>
                      ))}
                    </select>
                    <svg
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1">
                  <label htmlFor="filter-type" className={labelClass}>
                    Filter by type
                  </label>
                  <div className="relative">
                    <select
                      id="filter-type"
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value)}
                      className={selectClass}
                    >
                      <option value="">All Types</option>
                      {ENTRY_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                    <svg
                      className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="m6 9 6 6 6-6" />
                    </svg>
                  </div>
                </div>
              </div>
            </MotionReveal>

            {/* ── New entry form ────────────────────────────────────────── */}
            {showForm && (
              <MotionReveal delay={0}>
                <form
                  id="new-entry-form"
                  onSubmit={handleSubmit}
                  aria-label="New journal entry"
                  className="card-surface-elevated p-6 mb-8 space-y-4"
                >
                  <h2 className="font-display text-lg font-medium text-text mb-2">
                    New Entry
                  </h2>

                  <div>
                    <label htmlFor="form-title" className={labelClass}>
                      Title
                    </label>
                    <input
                      id="form-title"
                      type="text"
                      placeholder="Give this entry a title…"
                      value={formTitle}
                      onChange={(e) => setFormTitle(e.target.value)}
                      className={inputClass}
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="form-content" className={labelClass}>
                      Your thoughts
                    </label>
                    <textarea
                      id="form-content"
                      placeholder="Write freely — this is your space…"
                      value={formContent}
                      onChange={(e) => setFormContent(e.target.value)}
                      rows={5}
                      className={`${inputClass} resize-y`}
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="form-system" className={labelClass}>
                        System
                      </label>
                      <div className="relative">
                        <select
                          id="form-system"
                          value={formSystem}
                          onChange={(e) => setFormSystem(e.target.value)}
                          className={selectClass}
                        >
                          {SYSTEMS.map((s) => (
                            <option key={s} value={s}>
                              {s.charAt(0).toUpperCase() + s.slice(1)}
                            </option>
                          ))}
                        </select>
                        <svg
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="m6 9 6 6 6-6" />
                        </svg>
                      </div>
                    </div>

                    <div>
                      <label htmlFor="form-type" className={labelClass}>
                        Entry type
                      </label>
                      <div className="relative">
                        <select
                          id="form-type"
                          value={formType}
                          onChange={(e) => setFormType(e.target.value)}
                          className={selectClass}
                        >
                          {ENTRY_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {t.charAt(0).toUpperCase() + t.slice(1)}
                            </option>
                          ))}
                        </select>
                        <svg
                          className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text/30 pointer-events-none"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="m6 9 6 6 6-6" />
                        </svg>
                      </div>
                    </div>

                    <div>
                      <label htmlFor="form-mood" className={labelClass}>
                        Mood score — {formMood}/10{" "}
                        <span aria-label={moodLabel(formMood)}>
                          {moodEmoji(formMood)}
                        </span>
                      </label>
                      <input
                        id="form-mood"
                        type="range"
                        min={1}
                        max={10}
                        value={formMood}
                        onChange={(e) => setFormMood(Number(e.target.value))}
                        aria-valuemin={1}
                        aria-valuemax={10}
                        aria-valuenow={formMood}
                        aria-valuetext={`${formMood} — ${moodLabel(formMood)}`}
                        className="w-full accent-primary mt-2 h-1.5"
                      />
                    </div>

                    <div>
                      <label htmlFor="form-tags" className={labelClass}>
                        Tags{" "}
                        <span className="text-text/25 font-normal">
                          (comma-separated)
                        </span>
                      </label>
                      <input
                        id="form-tags"
                        type="text"
                        placeholder="growth, insight, clarity"
                        value={formTags}
                        onChange={(e) => setFormTags(e.target.value)}
                        className={inputClass}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-1">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="touch-target inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
                    >
                      {submitting ? (
                        <>
                          <span
                            className="w-4 h-4 border-2 border-bg/30 border-t-bg rounded-full animate-spin"
                            aria-hidden="true"
                          />
                          Saving…
                        </>
                      ) : (
                        <>
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
                            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
                            <polyline points="17 21 17 13 7 13 7 21" />
                            <polyline points="7 3 7 8 15 8" />
                          </svg>
                          Save Entry
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowForm(false)}
                      className="touch-target px-5 py-2.5 border border-white/[0.08] text-text/40 font-body text-sm rounded-xl hover:bg-white/[0.03] hover:text-text/60 hover:border-white/[0.12] transition-all duration-300"
                    >
                      Discard
                    </button>
                  </div>
                </form>
              </MotionReveal>
            )}

            {/* ── Error banner ─────────────────────────────────────────── */}
            {error && (
              <MotionReveal delay={0}>
                <div
                  role="alert"
                  className="flex items-start gap-3 bg-primary-dark/[0.08] border border-primary-dark/[0.18] text-primary-dark text-sm font-body rounded-xl px-4 py-3 mb-6"
                >
                  <svg
                    className="w-4 h-4 flex-shrink-0 mt-0.5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  {error}
                </div>
              </MotionReveal>
            )}

            {/* ── Loading state ─────────────────────────────────────────── */}
            {loading && (
              <div
                className="flex flex-col items-center gap-4 py-20"
                role="status"
                aria-label="Loading journal entries"
              >
                <span
                  className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin"
                  aria-hidden="true"
                />
                <p className="text-sm font-body text-text/35">
                  Loading journal entries…
                </p>
              </div>
            )}

            {/* ── Empty state ───────────────────────────────────────────── */}
            {!loading && entries.length === 0 && (
              <MotionReveal delay={0.1}>
                <div className="card-surface flex flex-col items-center gap-5 py-16 px-6 text-center">
                  <div className="w-16 h-16 rounded-2xl bg-primary/[0.06] border border-primary/[0.12] flex items-center justify-center">
                    <svg
                      className="w-7 h-7 text-primary/50"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="M12 20h9" />
                      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
                    </svg>
                  </div>
                  <div>
                    <h2 className="font-display text-xl font-light text-text mb-2">
                      Your journal awaits
                    </h2>
                    <p className="text-sm font-body text-text/35 max-w-xs">
                      Begin your reflection practice — write your first entry
                      and start tracking patterns across your transformation
                      journey.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowForm(true)}
                    className="touch-target inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-primary-dark via-primary to-primary-light text-bg font-body font-medium text-sm rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(218,165,32,0.25)] hover:scale-[1.02] active:scale-[0.98]"
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
                      <path d="M12 5v14" />
                      <path d="M5 12h14" />
                    </svg>
                    Write First Entry
                  </button>
                </div>
              </MotionReveal>
            )}

            {/* ── Entries list ──────────────────────────────────────────── */}
            {!loading && entries.length > 0 && (
              <MotionStagger
                staggerDelay={0.06}
                className="flex flex-col gap-3"
              >
                {entries.map((entry) => {
                  const colors = getSystemColors(entry.system);
                  return (
                    <MotionStaggerItem key={entry.id}>
                      <button
                        onClick={() => setSelectedEntry(entry)}
                        className={`group w-full text-left card-surface border-l-4 ${colors.border} px-5 py-4 hover:-translate-y-0.5 hover:border-opacity-100 transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40`}
                        aria-label={`Open journal entry: ${entry.title}`}
                      >
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <h3 className="font-display text-base font-medium text-text group-hover:text-text/90 transition-colors">
                            {entry.title}
                          </h3>
                          {entry.mood_score !== null && (
                            <span
                              className="text-xl flex-shrink-0"
                              aria-label={`Mood: ${moodLabel(entry.mood_score)}`}
                            >
                              {moodEmoji(entry.mood_score)}
                            </span>
                          )}
                        </div>
                        <p className="text-sm font-body text-text/35 mb-3 leading-relaxed">
                          {entry.content.length > 120
                            ? entry.content.slice(0, 120) + "…"
                            : entry.content}
                        </p>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.65rem] font-body font-medium ${colors.badge}`}
                          >
                            <span
                              className={`w-1 h-1 rounded-full ${colors.dot}`}
                              aria-hidden="true"
                            />
                            {entry.system}
                          </span>
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.65rem] font-body font-medium bg-white/[0.04] text-text/40">
                            {entry.entry_type}
                          </span>
                          <time
                            dateTime={entry.created_at}
                            className="ml-auto text-[0.65rem] font-body text-text/25"
                          >
                            {new Date(entry.created_at).toLocaleDateString(
                              undefined,
                              {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              },
                            )}
                          </time>
                        </div>
                      </button>
                    </MotionStaggerItem>
                  );
                })}
              </MotionStagger>
            )}
          </div>
        </div>

        {/* ── Entry detail modal ────────────────────────────────────────── */}
        {selectedEntry && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label={selectedEntry.title}
            className="fixed inset-0 bg-bg/80 backdrop-blur-sm flex items-center justify-center z-50 px-4 py-8"
            onClick={() => setSelectedEntry(null)}
          >
            <div
              className="card-surface-elevated w-full max-w-2xl max-h-[80vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal header */}
              <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4 border-b border-white/[0.06]">
                <h2 className="font-display text-xl font-medium text-text leading-snug">
                  {selectedEntry.title}
                </h2>
                <button
                  ref={modalCloseRef}
                  onClick={() => setSelectedEntry(null)}
                  aria-label="Close entry"
                  className="touch-target flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg text-text/40 hover:text-text/70 hover:bg-white/[0.05] transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  <svg
                    className="w-5 h-5"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M18 6 6 18" />
                    <path d="m6 6 12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal body */}
              <div className="px-6 py-5 space-y-5">
                {/* Metadata badges */}
                <div className="flex flex-wrap gap-2">
                  {(() => {
                    const colors = getSystemColors(selectedEntry.system);
                    return (
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-body font-medium ${colors.badge}`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${colors.dot}`}
                          aria-hidden="true"
                        />
                        {selectedEntry.system}
                      </span>
                    );
                  })()}

                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-body font-medium bg-white/[0.05] text-text/40">
                    {selectedEntry.entry_type}
                  </span>

                  {selectedEntry.mood_score !== null && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-body font-medium bg-accent/[0.08] text-accent/70">
                      <span
                        aria-label={`Mood: ${moodLabel(selectedEntry.mood_score)}`}
                      >
                        {moodEmoji(selectedEntry.mood_score)}
                      </span>
                      <span>
                        {selectedEntry.mood_score}/10 —{" "}
                        {moodLabel(selectedEntry.mood_score)}
                      </span>
                    </span>
                  )}
                </div>

                {/* Entry content */}
                <p className="text-sm font-body text-text/60 leading-[1.8] whitespace-pre-wrap">
                  {selectedEntry.content}
                </p>

                {/* Tags */}
                {selectedEntry.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {selectedEntry.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center px-2 py-0.5 rounded-full text-[0.65rem] font-body font-medium bg-white/[0.03] border border-white/[0.06] text-text/30"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Timestamp */}
                <time
                  dateTime={selectedEntry.created_at}
                  className="block text-xs font-body text-text/20"
                >
                  {new Date(selectedEntry.created_at).toLocaleString(
                    undefined,
                    {
                      weekday: "long",
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    },
                  )}
                </time>
              </div>
            </div>
          </div>
        )}
      </main>
    </ProtectedRoute>
  );
}

// ── StatCard sub-component ────────────────────────────────────────────────────

type StatAccent = "primary" | "secondary" | "accent";

function StatCard({
  label,
  value,
  accent = "primary",
}: {
  label: string;
  value: string | number;
  accent?: StatAccent;
}) {
  const textColorMap: Record<StatAccent, string> = {
    primary: "text-primary",
    secondary: "text-secondary-light",
    accent: "text-accent",
  };

  return (
    <div className="card-surface px-4 py-3 text-center">
      <div
        className={`font-display text-xl font-medium ${textColorMap[accent]} mb-0.5`}
      >
        {value}
      </div>
      <div className="text-[0.65rem] font-body text-text/30 uppercase tracking-wider">
        {label}
      </div>
    </div>
  );
}
