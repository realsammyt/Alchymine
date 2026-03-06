"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminGetInviteCodes,
  adminCreateInviteCode,
  adminBulkCreateInviteCodes,
  adminUpdateInviteCode,
  adminDeleteInviteCode,
} from "@/lib/api";
import type {
  InviteCode as InviteCodeType,
  PaginatedInviteCodes,
} from "@/lib/api";

export default function AdminInviteCodesPage() {
  const [data, setData] = useState<PaginatedInviteCodes | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [createMode, setCreateMode] = useState<"single" | "bulk">("single");
  const [newCode, setNewCode] = useState("");
  const [maxUses, setMaxUses] = useState(1);
  const [expiresAt, setExpiresAt] = useState("");
  const [note, setNote] = useState("");
  const [bulkCount, setBulkCount] = useState(5);
  const [creating, setCreating] = useState(false);

  const fetchCodes = useCallback(async () => {
    setLoading(true);
    try {
      const result = await adminGetInviteCodes({ page, perPage: 20 });
      setData(result);
    } catch {
      // handle error
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchCodes();
  }, [fetchCodes]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      if (createMode === "single") {
        await adminCreateInviteCode({
          code: newCode || undefined,
          max_uses: maxUses,
          expires_at: expiresAt || undefined,
          note: note || undefined,
        });
      } else {
        await adminBulkCreateInviteCodes({
          count: bulkCount,
          max_uses: maxUses,
          expires_at: expiresAt || undefined,
          note: note || undefined,
        });
      }
      setShowCreate(false);
      setNewCode("");
      setNote("");
      setExpiresAt("");
      fetchCodes();
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (code: InviteCodeType) => {
    await adminUpdateInviteCode(code.id, { is_active: false });
    fetchCodes();
  };

  const handleDelete = async (code: InviteCodeType) => {
    if (code.uses_count > 0) return;
    await adminDeleteInviteCode(code.id);
    fetchCodes();
  };

  const copyCode = (code: InviteCodeType) => {
    navigator.clipboard.writeText(code.code);
    setCopiedId(code.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display text-text font-light">
            Invite Codes
          </h1>
          <p className="text-sm text-text/50 mt-1">
            {data ? `${data.total} total codes` : "Loading..."}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors"
        >
          {showCreate ? "Cancel" : "Create Code"}
        </button>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-surface border border-white/5 rounded-xl p-6 space-y-4">
          <div className="flex gap-4">
            <button
              onClick={() => setCreateMode("single")}
              className={`text-sm px-3 py-1 rounded ${createMode === "single" ? "bg-primary/10 text-primary" : "text-text/40"}`}
            >
              Single
            </button>
            <button
              onClick={() => setCreateMode("bulk")}
              className={`text-sm px-3 py-1 rounded ${createMode === "bulk" ? "bg-primary/10 text-primary" : "text-text/40"}`}
            >
              Bulk
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {createMode === "single" ? (
              <div>
                <label className="block text-xs text-text/40 mb-1">
                  Code (leave empty to auto-generate)
                </label>
                <input
                  type="text"
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  placeholder="Auto-generated"
                  className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder:text-text/20 focus:outline-none focus:border-primary/50"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs text-text/40 mb-1">
                  Number of codes (1-100)
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={bulkCount}
                  onChange={(e) => setBulkCount(Number(e.target.value))}
                  className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50"
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-text/40 mb-1">
                Max uses per code
              </label>
              <input
                type="number"
                min={1}
                value={maxUses}
                onChange={(e) => setMaxUses(Number(e.target.value))}
                className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50"
              />
            </div>
            <div>
              <label className="block text-xs text-text/40 mb-1">
                Expires at (optional)
              </label>
              <input
                type="datetime-local"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
                className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50"
              />
            </div>
            <div>
              <label className="block text-xs text-text/40 mb-1">
                Note (optional)
              </label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={255}
                placeholder="e.g. Beta testers batch 1"
                className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder:text-text/20 focus:outline-none focus:border-primary/50"
              />
            </div>
          </div>

          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 text-sm bg-primary text-bg rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {creating
              ? "Creating..."
              : createMode === "single"
                ? "Create Code"
                : `Create ${bulkCount} Codes`}
          </button>
        </div>
      )}

      {/* Codes Table */}
      <div className="bg-surface border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5 text-text/40 text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-3">Code</th>
              <th className="text-left px-4 py-3">Uses</th>
              <th className="text-left px-4 py-3">Expires</th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Note</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text/40">
                  <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full mx-auto" />
                </td>
              </tr>
            ) : data?.codes.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text/40">
                  No invite codes yet
                </td>
              </tr>
            ) : (
              data?.codes.map((code) => (
                <tr
                  key={code.id}
                  className="border-b border-white/5 hover:bg-white/[0.02]"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono text-primary bg-primary/5 px-2 py-0.5 rounded">
                        {code.code}
                      </code>
                      <button
                        onClick={() => copyCode(code)}
                        className="text-text/30 hover:text-text/60 transition-colors"
                        title="Copy code"
                      >
                        {copiedId === code.id ? (
                          <span className="text-green-400 text-xs">
                            Copied!
                          </span>
                        ) : (
                          <svg
                            className="w-4 h-4"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <rect
                              x="9"
                              y="9"
                              width="13"
                              height="13"
                              rx="2"
                              ry="2"
                            />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-text/60">
                    {code.uses_count} / {code.max_uses}
                  </td>
                  <td className="px-4 py-3 text-text/60 text-xs">
                    {code.expires_at
                      ? new Date(code.expires_at).toLocaleString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs ${
                        code.is_active
                          ? "bg-green-500/10 text-green-400"
                          : "bg-red-500/10 text-red-400"
                      }`}
                    >
                      {code.is_active ? "Active" : "Revoked"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text/40 text-xs max-w-[150px] truncate">
                    {code.note || "—"}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    {code.is_active && (
                      <button
                        onClick={() => handleRevoke(code)}
                        className="text-xs px-2 py-1 border border-amber-500/20 text-amber-400 rounded hover:bg-amber-500/10 transition-colors"
                      >
                        Revoke
                      </button>
                    )}
                    {code.uses_count === 0 && (
                      <button
                        onClick={() => handleDelete(code)}
                        className="text-xs px-2 py-1 border border-red-500/20 text-red-400 rounded hover:bg-red-500/10 transition-colors"
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
          <p className="text-xs text-text/40">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 text-xs border border-white/10 rounded text-text/60 hover:text-text disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 text-xs border border-white/10 rounded text-text/60 hover:text-text disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
