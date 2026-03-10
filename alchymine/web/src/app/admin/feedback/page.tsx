"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listAdminFeedback, patchFeedback } from "@/lib/api";
import type { FeedbackItem, PaginatedFeedback } from "@/lib/api";

type StatusFilter = "all" | "new" | "reviewed" | "resolved" | "dismissed";
type CategoryFilter =
  | "all"
  | "general"
  | "bug"
  | "feature"
  | "praise"
  | "other";

const STATUS_STYLES: Record<FeedbackItem["status"], string> = {
  new: "bg-blue-500/10 text-blue-400",
  reviewed: "bg-amber-500/10 text-amber-400",
  resolved: "bg-green-500/10 text-green-400",
  dismissed: "bg-white/5 text-text/40",
};

const STATUS_OPTIONS: FeedbackItem["status"][] = [
  "new",
  "reviewed",
  "resolved",
  "dismissed",
];

function StatusBadge({ status }: { status: FeedbackItem["status"] }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs ${STATUS_STYLES[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

function DetailDrawer({
  item,
  onClose,
  onUpdate,
}: {
  item: FeedbackItem;
  onClose: () => void;
  onUpdate: (updated: FeedbackItem) => void;
}) {
  const [adminNote, setAdminNote] = useState(item.admin_note ?? "");
  const [status, setStatus] = useState<FeedbackItem["status"]>(item.status);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await patchFeedback(item.id, {
        status,
        admin_note: adminNote,
      });
      onUpdate(updated);
    } catch {
      setSaveError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex justify-end"
      onClick={handleOverlayClick}
      aria-modal="true"
      role="dialog"
      aria-label="Feedback detail"
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40" aria-hidden="true" />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-surface border-l border-white/10 flex flex-col h-full overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <h2 className="font-display text-lg text-text font-light">
            Feedback #{item.id}
          </h2>
          <button
            onClick={onClose}
            className="text-text/40 hover:text-text transition-colors p-1 rounded"
            aria-label="Close detail panel"
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
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 px-6 py-5 space-y-5">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
                Category
              </p>
              <p className="font-body text-sm text-text capitalize">
                {item.category}
              </p>
            </div>
            <div>
              <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
                Date
              </p>
              <p className="font-body text-sm text-text">
                {new Date(item.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="col-span-2">
              <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
                Email
              </p>
              <p className="font-body text-sm text-text">
                {item.email ?? (
                  <span className="text-text/40 italic">Anonymous</span>
                )}
              </p>
            </div>
            {item.page_url && (
              <div className="col-span-2">
                <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-1">
                  Page URL
                </p>
                <p className="font-body text-xs text-text/60 break-all">
                  {item.page_url}
                </p>
              </div>
            )}
          </div>

          {/* Message */}
          <div>
            <p className="font-body text-xs text-text/40 uppercase tracking-wider mb-2">
              Message
            </p>
            <div className="bg-bg/50 border border-white/5 rounded-lg px-4 py-3">
              <p className="font-body text-sm text-text leading-relaxed whitespace-pre-wrap">
                {item.message}
              </p>
            </div>
          </div>

          {/* Status */}
          <div>
            <label
              htmlFor="drawer-status"
              className="font-body text-xs text-text/40 uppercase tracking-wider block mb-2"
            >
              Status
            </label>
            <select
              id="drawer-status"
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as FeedbackItem["status"])
              }
              className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm font-body text-text focus:outline-none focus:border-primary/40"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Admin note */}
          <div>
            <label
              htmlFor="drawer-note"
              className="font-body text-xs text-text/40 uppercase tracking-wider block mb-2"
            >
              Admin Note
            </label>
            <textarea
              id="drawer-note"
              value={adminNote}
              onChange={(e) => setAdminNote(e.target.value)}
              rows={4}
              className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm font-body text-text focus:outline-none focus:border-primary/40 resize-none"
              placeholder="Internal notes visible only to admins..."
            />
          </div>

          {saveError && (
            <p className="text-xs font-body text-red-400">{saveError}</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/5">
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

const STATUS_FILTERS: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "all" },
  { label: "New", value: "new" },
  { label: "Reviewed", value: "reviewed" },
  { label: "Resolved", value: "resolved" },
  { label: "Dismissed", value: "dismissed" },
];

const CATEGORY_FILTERS: { label: string; value: CategoryFilter }[] = [
  { label: "All", value: "all" },
  { label: "General", value: "general" },
  { label: "Bug", value: "bug" },
  { label: "Feature", value: "feature" },
  { label: "Praise", value: "praise" },
  { label: "Other", value: "other" },
];

export default function AdminFeedbackPage() {
  const [data, setData] = useState<PaginatedFeedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [selected, setSelected] = useState<FeedbackItem | null>(null);

  const fetchFeedback = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listAdminFeedback({
        page,
        perPage: 25,
        status: statusFilter === "all" ? undefined : statusFilter,
        category: categoryFilter === "all" ? undefined : categoryFilter,
      });
      setData(result);
    } catch {
      // handle error silently
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, categoryFilter]);

  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  const handleStatusFilterChange = (filter: StatusFilter) => {
    setStatusFilter(filter);
    setPage(1);
  };

  const handleCategoryFilterChange = (filter: CategoryFilter) => {
    setCategoryFilter(filter);
    setPage(1);
  };

  const handleStatusChange = async (
    item: FeedbackItem,
    newStatus: FeedbackItem["status"],
  ) => {
    try {
      const updated = await patchFeedback(item.id, { status: newStatus });
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((i) => (i.id === updated.id ? updated : i)),
            }
          : prev,
      );
      if (selected?.id === updated.id) {
        setSelected(updated);
      }
    } catch {
      // handle error silently
    }
  };

  const handleDrawerUpdate = (updated: FeedbackItem) => {
    setData((prev) =>
      prev
        ? {
            ...prev,
            items: prev.items.map((i) => (i.id === updated.id ? updated : i)),
          }
        : prev,
    );
    setSelected(updated);
  };

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl text-text font-light">Feedback</h1>
        <p className="font-body text-sm text-text/50 mt-1">
          {data ? `${data.total} total entries` : "Loading..."}
        </p>
      </div>

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => handleStatusFilterChange(f.value)}
              className={`px-4 py-1.5 text-sm font-body rounded-lg transition-colors ${
                statusFilter === f.value
                  ? "bg-primary/10 text-primary"
                  : "text-text/40 hover:text-text/60 hover:bg-white/5"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {CATEGORY_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => handleCategoryFilterChange(f.value)}
              className={`px-3 py-1 text-xs font-body rounded-lg transition-colors ${
                categoryFilter === f.value
                  ? "bg-white/10 text-text"
                  : "text-text/30 hover:text-text/50 hover:bg-white/5"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full font-body text-sm">
          <thead>
            <tr className="border-b border-white/5 text-text/40 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3">Date</th>
              <th className="text-left px-4 py-3">Category</th>
              <th className="text-left px-4 py-3">Message</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text/40">
                  <div
                    className="w-6 h-6 rounded-full border-2 border-primary/20 border-t-primary animate-spin mx-auto"
                    role="status"
                    aria-label="Loading"
                  />
                </td>
              </tr>
            ) : data?.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text/40">
                  No feedback entries found
                </td>
              </tr>
            ) : (
              data?.items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => setSelected(item)}
                  className="border-b border-white/5 hover:bg-white/[0.02] transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 text-text/60 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-text capitalize">
                    {item.category}
                  </td>
                  <td className="px-4 py-3 text-text/80 max-w-xs">
                    <span className="line-clamp-1">{item.message}</span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <select
                      value={item.status}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        e.stopPropagation();
                        handleStatusChange(
                          item,
                          e.target.value as FeedbackItem["status"],
                        );
                      }}
                      className="bg-bg border border-white/10 rounded px-2 py-1 text-xs font-body text-text/60 focus:outline-none focus:border-primary/40 cursor-pointer"
                      aria-label={`Change status for feedback #${item.id}`}
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>
                          {s.charAt(0).toUpperCase() + s.slice(1)}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="font-body text-xs text-text/40">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 font-body text-xs border border-white/10 rounded text-text/60 hover:text-text disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 font-body text-xs border border-white/10 rounded text-text/60 hover:text-text disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Detail Drawer */}
      {selected && (
        <DetailDrawer
          item={selected}
          onClose={() => setSelected(null)}
          onUpdate={handleDrawerUpdate}
        />
      )}
    </div>
  );
}
