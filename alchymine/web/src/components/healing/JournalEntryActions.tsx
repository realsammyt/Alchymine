"use client";

import { useState, useCallback } from "react";
import {
  updateJournalEntry,
  deleteJournalEntry,
  JournalEntry,
} from "@/lib/api";
import Button from "@/components/shared/Button";

// ── Props ────────────────────────────────────────────────────────────

interface JournalEntryActionsProps {
  /** The journal entry to act on. */
  entry: JournalEntry;
  /** Called after a successful update with the updated entry. */
  onUpdated?: (updated: JournalEntry) => void;
  /** Called after a successful deletion. */
  onDeleted?: (entryId: string) => void;
}

// ── Component ────────────────────────────────────────────────────────

export default function JournalEntryActions({
  entry,
  onUpdated,
  onDeleted,
}: JournalEntryActionsProps) {
  const [mode, setMode] = useState<"view" | "edit" | "confirm-delete">("view");
  const [editTitle, setEditTitle] = useState(entry.title);
  const [editContent, setEditContent] = useState(entry.content);
  const [editMoodScore, setEditMoodScore] = useState<number | null>(
    entry.mood_score,
  );
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateJournalEntry(entry.id, {
        title: editTitle,
        content: editContent,
        mood_score: editMoodScore,
      });
      onUpdated?.(updated);
      setMode("view");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }, [entry.id, editTitle, editContent, editMoodScore, onUpdated]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    setError(null);
    try {
      await deleteJournalEntry(entry.id);
      onDeleted?.(entry.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete entry");
      setDeleting(false);
    }
  }, [entry.id, onDeleted]);

  const handleCancelEdit = useCallback(() => {
    setEditTitle(entry.title);
    setEditContent(entry.content);
    setEditMoodScore(entry.mood_score);
    setError(null);
    setMode("view");
  }, [entry]);

  // ── View mode: show entry with edit / delete buttons ──────────

  if (mode === "view") {
    return (
      <div data-testid="journal-entry-actions" role="region" aria-label={`Journal entry: ${entry.title}`}>
        {/* Entry display */}
        <div className="mb-4">
          <h3 className="font-display text-lg font-light text-text mb-1">
            {entry.title}
          </h3>
          <div className="flex items-center gap-2 text-xs font-body text-text/40 mb-3">
            <span>{entry.system}</span>
            <span aria-hidden="true">|</span>
            <span>{entry.entry_type}</span>
            {entry.mood_score !== null && (
              <>
                <span aria-hidden="true">|</span>
                <span>Mood: {entry.mood_score}/10</span>
              </>
            )}
          </div>
          <p className="font-body text-sm text-text/70 leading-relaxed whitespace-pre-wrap">
            {entry.content}
          </p>
          {entry.tags.length > 0 && (
            <div
              className="flex flex-wrap gap-1.5 mt-3"
              role="list"
              aria-label="Tags"
            >
              {entry.tags.map((tag) => (
                <span
                  key={tag}
                  role="listitem"
                  className="px-2 py-0.5 rounded-full text-xs font-body bg-white/5 text-text/50 border border-white/10"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setMode("edit")}
            data-testid="journal-edit-btn"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mr-1"
            >
              <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
            Edit
          </Button>
          <button
            onClick={() => setMode("confirm-delete")}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm font-body font-medium rounded-lg border border-red-400/30 text-red-400 hover:bg-red-400/10 transition-colors"
            data-testid="journal-delete-btn"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18" />
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            </svg>
            Delete
          </button>
        </div>
      </div>
    );
  }

  // ── Delete confirmation ────────────────────────────────────────

  if (mode === "confirm-delete") {
    return (
      <div data-testid="journal-delete-confirm" role="alertdialog" aria-label="Confirm deletion">
        <div className="bg-red-400/10 border border-red-400/20 rounded-xl p-4 mb-4">
          <p className="font-body text-sm text-red-400 mb-1 font-medium">
            Delete this journal entry?
          </p>
          <p className="font-body text-xs text-text/50">
            This action cannot be undone. The entry &ldquo;{entry.title}&rdquo;
            will be permanently removed.
          </p>
        </div>
        {error && (
          <p className="font-body text-sm text-red-400 mb-3">{error}</p>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="inline-flex items-center gap-1 px-4 py-2 text-sm font-body font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 disabled:opacity-50 transition-colors"
            data-testid="journal-confirm-delete-btn"
            aria-label={deleting ? "Deleting journal entry" : `Confirm delete ${entry.title}`}
          >
            {deleting ? "Deleting..." : "Yes, Delete"}
          </button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setError(null);
              setMode("view");
            }}
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  // ── Edit mode ──────────────────────────────────────────────────

  return (
    <div data-testid="journal-edit-form" role="form" aria-label={`Edit journal entry: ${entry.title}`}>
      <div className="space-y-4 mb-4">
        {/* Title */}
        <div>
          <label
            htmlFor="edit-title"
            className="block font-body text-xs text-text/40 uppercase tracking-wider mb-1"
          >
            Title
          </label>
          <input
            id="edit-title"
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder:text-text/30 focus:outline-none focus:border-accent/50"
            data-testid="journal-edit-title"
          />
        </div>

        {/* Content */}
        <div>
          <label
            htmlFor="edit-content"
            className="block font-body text-xs text-text/40 uppercase tracking-wider mb-1"
          >
            Content
          </label>
          <textarea
            id="edit-content"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            rows={6}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder:text-text/30 focus:outline-none focus:border-accent/50 resize-y"
            data-testid="journal-edit-content"
          />
        </div>

        {/* Mood score */}
        <div>
          <label
            htmlFor="edit-mood"
            className="block font-body text-xs text-text/40 uppercase tracking-wider mb-1"
          >
            Mood Score (1-10)
          </label>
          <input
            id="edit-mood"
            type="number"
            min={1}
            max={10}
            value={editMoodScore ?? ""}
            onChange={(e) => {
              const v = e.target.value;
              setEditMoodScore(v === "" ? null : Math.min(10, Math.max(1, Number(v))));
            }}
            className="w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-2 font-body text-sm text-text placeholder:text-text/30 focus:outline-none focus:border-accent/50"
            placeholder="-"
            data-testid="journal-edit-mood"
          />
        </div>
      </div>

      {error && (
        <p className="font-body text-sm text-red-400 mb-3">{error}</p>
      )}

      <div className="flex gap-2">
        <Button
          variant="primary"
          size="sm"
          loading={saving}
          onClick={handleSave}
          data-testid="journal-save-btn"
        >
          Save Changes
        </Button>
        <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
