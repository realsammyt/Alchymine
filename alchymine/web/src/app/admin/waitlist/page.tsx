"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminGetWaitlist,
  adminInviteWaitlistEntries,
  adminDeleteWaitlistEntry,
} from "@/lib/api";
import type {
  WaitlistEntry,
  PaginatedWaitlist,
  WaitlistInviteResult,
} from "@/lib/api";

type StatusFilter = "all" | "pending" | "invited" | "registered";

function StatusBadge({ status }: { status: WaitlistEntry["status"] }) {
  const styles: Record<WaitlistEntry["status"], string> = {
    pending: "bg-amber-500/10 text-amber-400",
    invited: "bg-blue-500/10 text-blue-400",
    registered: "bg-green-500/10 text-green-400",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-xs ${styles[status]}`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default function AdminWaitlistPage() {
  const [data, setData] = useState<PaginatedWaitlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [inviting, setInviting] = useState(false);
  const [inviteResults, setInviteResults] = useState<
    WaitlistInviteResult[] | null
  >(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const fetchWaitlist = useCallback(async () => {
    setLoading(true);
    try {
      const result = await adminGetWaitlist({
        page,
        perPage: 20,
        status: statusFilter === "all" ? undefined : statusFilter,
      });
      setData(result);
      setSelectedIds(new Set());
    } catch {
      // handle error silently
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchWaitlist();
  }, [fetchWaitlist]);

  const handleFilterChange = (filter: StatusFilter) => {
    setStatusFilter(filter);
    setPage(1);
    setSelectedIds(new Set());
    setInviteResults(null);
    setInviteError(null);
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    const pendingEntries = (data?.entries ?? []).filter(
      (e) => e.status === "pending",
    );
    const allSelected = pendingEntries.every((e) => selectedIds.has(e.id));
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(pendingEntries.map((e) => e.id)));
    }
  };

  const handleSendInvites = async () => {
    if (selectedIds.size === 0) return;
    setInviting(true);
    setInviteResults(null);
    setInviteError(null);
    try {
      const result = await adminInviteWaitlistEntries({
        entry_ids: Array.from(selectedIds),
      });
      setInviteResults(result.results);
      setSelectedIds(new Set());
      fetchWaitlist();
    } catch {
      setInviteError("Failed to send invites. Please try again.");
    } finally {
      setInviting(false);
    }
  };

  const handleDelete = async (entry: WaitlistEntry) => {
    if (entry.status !== "pending") return;
    try {
      await adminDeleteWaitlistEntry(entry.id);
      fetchWaitlist();
    } catch {
      // handle error silently
    }
  };

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;
  const pendingEntries = (data?.entries ?? []).filter(
    (e) => e.status === "pending",
  );
  const allPendingSelected =
    pendingEntries.length > 0 &&
    pendingEntries.every((e) => selectedIds.has(e.id));

  const FILTERS: { label: string; value: StatusFilter }[] = [
    { label: "All", value: "all" },
    { label: "Pending", value: "pending" },
    { label: "Invited", value: "invited" },
    { label: "Registered", value: "registered" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl text-text font-light">
            Waitlist
          </h1>
          <p className="font-body text-sm text-text/50 mt-1">
            {data ? `${data.total} total entries` : "Loading..."}
          </p>
        </div>
        <button
          onClick={handleSendInvites}
          disabled={selectedIds.size === 0 || inviting}
          className="px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {inviting
            ? "Sending..."
            : selectedIds.size > 0
              ? `Send ${selectedIds.size} Invite${selectedIds.size !== 1 ? "s" : ""}`
              : "Send Invites"}
        </button>
      </div>

      {/* Invite results */}
      {inviteResults && (
        <div className="bg-surface border border-white/5 rounded-xl p-4 space-y-2">
          <p className="text-xs font-body text-text/50 uppercase tracking-wider mb-3">
            Invite Results
          </p>
          {inviteResults.map((r) => (
            <div
              key={r.email}
              className="flex items-center gap-3 text-sm font-body py-1"
            >
              <span
                className={`w-2 h-2 rounded-full flex-shrink-0 ${r.success ? "bg-green-400" : "bg-red-400"}`}
              />
              <span className="text-text/80 flex-1">{r.email}</span>
              {r.code && (
                <code className="text-xs font-mono text-primary/60 bg-primary/5 px-2 py-0.5 rounded">
                  {r.code}
                </code>
              )}
              {!r.success && r.error && (
                <span className="text-xs text-red-400">{r.error}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {inviteError && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-sm font-body text-red-400">
          {inviteError}
        </div>
      )}

      {/* Status filter tabs */}
      <div className="flex gap-1">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => handleFilterChange(f.value)}
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

      {/* Table */}
      <div className="bg-surface border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full font-body text-sm">
          <thead>
            <tr className="border-b border-white/5 text-text/40 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allPendingSelected}
                  onChange={toggleSelectAll}
                  disabled={pendingEntries.length === 0}
                  className="accent-primary cursor-pointer disabled:cursor-not-allowed"
                  aria-label="Select all pending entries"
                />
              </th>
              <th className="text-left px-4 py-3">Email</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Joined</th>
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
            ) : data?.entries.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text/40">
                  No waitlist entries found
                </td>
              </tr>
            ) : (
              data?.entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="px-4 py-3">
                    {entry.status === "pending" && (
                      <input
                        type="checkbox"
                        checked={selectedIds.has(entry.id)}
                        onChange={() => toggleSelect(entry.id)}
                        className="accent-primary cursor-pointer"
                        aria-label={`Select ${entry.email}`}
                      />
                    )}
                  </td>
                  <td className="px-4 py-3 text-text">{entry.email}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={entry.status} />
                  </td>
                  <td className="px-4 py-3 text-text/60">
                    {new Date(entry.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {entry.status === "pending" && (
                      <button
                        onClick={() => handleDelete(entry)}
                        className="text-xs px-3 py-1 border border-red-500/20 text-red-400 rounded hover:bg-red-500/10 transition-colors"
                      >
                        Delete
                      </button>
                    )}
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
    </div>
  );
}
