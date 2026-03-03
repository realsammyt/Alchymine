"use client";

import { useState, useEffect, useCallback } from "react";
import {
  createJournalEntry,
  getJournalEntries,
  getJournalStats,
  JournalEntry,
  JournalStatsResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

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

  const moodEmoji = (score: number | null) => {
    if (score === null) return "";
    if (score >= 8) return "😊";
    if (score >= 6) return "🙂";
    if (score >= 4) return "😐";
    if (score >= 2) return "😔";
    return "😢";
  };

  const systemColor = (system: string): string => {
    const colors: Record<string, string> = {
      intelligence: "#6366f1",
      healing: "#10b981",
      wealth: "#f59e0b",
      creative: "#ec4899",
      perspective: "#8b5cf6",
    };
    return colors[system] || "#6b7280";
  };

  if (!user) {
    return null;
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
        }}
      >
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Journal</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            background: "#6366f1",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "0.5rem 1.25rem",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          {showForm ? "Cancel" : "+ New Entry"}
        </button>
      </div>

      {/* Stats bar */}
      {stats && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "0.75rem",
            marginBottom: "1.5rem",
          }}
        >
          <StatCard label="Total Entries" value={stats.total_entries} />
          <StatCard label="Streak" value={`${stats.streak_days}d`} />
          <StatCard
            label="Avg Mood"
            value={
              stats.average_mood !== null
                ? `${stats.average_mood.toFixed(1)} ${moodEmoji(stats.average_mood)}`
                : "—"
            }
          />
          <StatCard label="Tags Used" value={stats.tags_used.length} />
        </div>
      )}

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
        }}
      >
        <select
          value={filterSystem}
          onChange={(e) => setFilterSystem(e.target.value)}
          style={selectStyle}
        >
          <option value="">All Systems</option>
          {SYSTEMS.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          style={selectStyle}
        >
          <option value="">All Types</option>
          {ENTRY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* New entry form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          style={{
            background: "#1e1e2e",
            borderRadius: 12,
            padding: "1.25rem",
            marginBottom: "1.5rem",
            border: "1px solid #333",
          }}
        >
          <input
            type="text"
            placeholder="Title"
            value={formTitle}
            onChange={(e) => setFormTitle(e.target.value)}
            style={inputStyle}
            required
          />
          <textarea
            placeholder="Write your thoughts..."
            value={formContent}
            onChange={(e) => setFormContent(e.target.value)}
            rows={5}
            style={{ ...inputStyle, resize: "vertical" }}
            required
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: "0.75rem",
            }}
          >
            <div>
              <label style={labelStyle}>System</label>
              <select
                value={formSystem}
                onChange={(e) => setFormSystem(e.target.value)}
                style={selectStyle}
              >
                {SYSTEMS.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Type</label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                style={selectStyle}
              >
                {ENTRY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>
                Mood (1-10): {formMood} {moodEmoji(formMood)}
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={formMood}
                onChange={(e) => setFormMood(Number(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label style={labelStyle}>Tags (comma-separated)</label>
              <input
                type="text"
                placeholder="growth, insight"
                value={formTags}
                onChange={(e) => setFormTags(e.target.value)}
                style={inputStyle}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={submitting}
            style={{
              background: "#6366f1",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "0.5rem 1.5rem",
              cursor: submitting ? "not-allowed" : "pointer",
              fontWeight: 600,
              marginTop: "0.75rem",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Save Entry"}
          </button>
        </form>
      )}

      {/* Error */}
      {error && (
        <div
          style={{
            color: "#ef4444",
            background: "#1e1e2e",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            marginBottom: "1rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ textAlign: "center", padding: "2rem", color: "#9ca3af" }}>
          Loading journal entries...
        </div>
      )}

      {/* Entry detail modal */}
      {selectedEntry && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
            padding: "1rem",
          }}
          onClick={() => setSelectedEntry(null)}
        >
          <div
            style={{
              background: "#1e1e2e",
              borderRadius: 16,
              padding: "1.5rem",
              maxWidth: 640,
              width: "100%",
              maxHeight: "80vh",
              overflow: "auto",
              border: "1px solid #333",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "start",
                marginBottom: "1rem",
              }}
            >
              <h2 style={{ fontSize: "1.25rem", fontWeight: 600 }}>
                {selectedEntry.title}
              </h2>
              <button
                onClick={() => setSelectedEntry(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#9ca3af",
                  fontSize: "1.25rem",
                  cursor: "pointer",
                }}
              >
                &times;
              </button>
            </div>
            <div
              style={{
                display: "flex",
                gap: "0.5rem",
                marginBottom: "1rem",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  ...tagStyle,
                  background: systemColor(selectedEntry.system) + "33",
                  color: systemColor(selectedEntry.system),
                }}
              >
                {selectedEntry.system}
              </span>
              <span
                style={{ ...tagStyle, background: "#374151", color: "#d1d5db" }}
              >
                {selectedEntry.entry_type}
              </span>
              {selectedEntry.mood_score !== null && (
                <span
                  style={{
                    ...tagStyle,
                    background: "#374151",
                    color: "#d1d5db",
                  }}
                >
                  Mood: {selectedEntry.mood_score}{" "}
                  {moodEmoji(selectedEntry.mood_score)}
                </span>
              )}
            </div>
            <p
              style={{
                color: "#d1d5db",
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
              }}
            >
              {selectedEntry.content}
            </p>
            {selectedEntry.tags.length > 0 && (
              <div
                style={{
                  display: "flex",
                  gap: "0.5rem",
                  marginTop: "1rem",
                  flexWrap: "wrap",
                }}
              >
                {selectedEntry.tags.map((tag) => (
                  <span
                    key={tag}
                    style={{
                      ...tagStyle,
                      background: "#1f2937",
                      color: "#9ca3af",
                      fontSize: "0.75rem",
                    }}
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}
            <p
              style={{
                color: "#6b7280",
                fontSize: "0.75rem",
                marginTop: "1rem",
              }}
            >
              {new Date(selectedEntry.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Entries list */}
      {!loading && entries.length === 0 && (
        <div style={{ textAlign: "center", padding: "3rem", color: "#6b7280" }}>
          <p style={{ fontSize: "1.25rem", marginBottom: "0.5rem" }}>
            No journal entries yet
          </p>
          <p>Start your reflection practice by creating your first entry.</p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {entries.map((entry) => (
          <div
            key={entry.id}
            onClick={() => setSelectedEntry(entry)}
            style={{
              background: "#1e1e2e",
              borderRadius: 12,
              padding: "1rem 1.25rem",
              cursor: "pointer",
              borderLeft: `4px solid ${systemColor(entry.system)}`,
              transition: "transform 0.15s",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "start",
              }}
            >
              <h3
                style={{
                  fontWeight: 600,
                  fontSize: "1rem",
                  marginBottom: "0.25rem",
                }}
              >
                {entry.title}
              </h3>
              {entry.mood_score !== null && (
                <span style={{ fontSize: "1.25rem" }}>
                  {moodEmoji(entry.mood_score)}
                </span>
              )}
            </div>
            <p
              style={{
                color: "#9ca3af",
                fontSize: "0.875rem",
                marginBottom: "0.5rem",
              }}
            >
              {entry.content.length > 120
                ? entry.content.slice(0, 120) + "..."
                : entry.content}
            </p>
            <div
              style={{
                display: "flex",
                gap: "0.5rem",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  ...tagStyle,
                  background: systemColor(entry.system) + "33",
                  color: systemColor(entry.system),
                  fontSize: "0.7rem",
                }}
              >
                {entry.system}
              </span>
              <span
                style={{
                  ...tagStyle,
                  background: "#374151",
                  color: "#9ca3af",
                  fontSize: "0.7rem",
                }}
              >
                {entry.entry_type}
              </span>
              <span
                style={{
                  color: "#6b7280",
                  fontSize: "0.75rem",
                  marginLeft: "auto",
                }}
              >
                {new Date(entry.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        background: "#1e1e2e",
        borderRadius: 10,
        padding: "0.75rem 1rem",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: "1.25rem", fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: "0.75rem", color: "#9ca3af" }}>{label}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "#111827",
  border: "1px solid #374151",
  borderRadius: 8,
  padding: "0.5rem 0.75rem",
  color: "#e5e7eb",
  fontSize: "0.875rem",
  marginBottom: "0.75rem",
  outline: "none",
};

const selectStyle: React.CSSProperties = {
  background: "#111827",
  border: "1px solid #374151",
  borderRadius: 8,
  padding: "0.5rem 0.75rem",
  color: "#e5e7eb",
  fontSize: "0.875rem",
  outline: "none",
  width: "100%",
};

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.75rem",
  color: "#9ca3af",
  marginBottom: "0.25rem",
};

const tagStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0.15rem 0.5rem",
  borderRadius: 99,
  fontSize: "0.75rem",
  fontWeight: 500,
};
