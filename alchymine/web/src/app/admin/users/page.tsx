"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  adminGetUsers,
  adminUpdateUserStatus,
  adminInviteUsers,
} from "@/lib/api";
import type {
  AdminUser,
  PaginatedUsers,
  InviteUsersResponse,
} from "@/lib/api";

export default function AdminUsersPage() {
  const router = useRouter();
  const [data, setData] = useState<PaginatedUsers | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");

  // Invite form state
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteNote, setInviteNote] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteResult, setInviteResult] = useState<InviteUsersResponse | null>(
    null,
  );

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const result = await adminGetUsers({
        page,
        perPage: 20,
        search: search || undefined,
        sortBy,
        sortOrder,
      });
      setData(result);
    } catch {
      // handle error
    } finally {
      setLoading(false);
    }
  }, [page, search, sortBy, sortOrder]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const toggleStatus = async (user: AdminUser) => {
    try {
      await adminUpdateUserStatus(user.id, !user.is_active);
      fetchUsers();
    } catch {
      // handle error
    }
  };

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  };

  const handleInvite = async () => {
    const emails = inviteEmail
      .split(/[,\n]+/)
      .map((e) => e.trim())
      .filter(Boolean);
    if (emails.length === 0) return;

    setInviting(true);
    setInviteResult(null);
    try {
      const result = await adminInviteUsers({
        emails,
        note: inviteNote || undefined,
      });
      setInviteResult(result);
      setInviteEmail("");
      setInviteNote("");
      fetchUsers();
    } catch {
      // handle error
    } finally {
      setInviting(false);
    }
  };

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl text-text font-light">Users</h1>
          <p className="font-body text-sm text-text/50 mt-1">
            {data ? `${data.total} total users` : "Loading..."}
          </p>
        </div>
        <button
          onClick={() => {
            setShowInvite(!showInvite);
            setInviteResult(null);
          }}
          className="px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-colors"
        >
          {showInvite ? "Cancel" : "Invite User"}
        </button>
      </div>

      {/* Invite Form */}
      {showInvite && (
        <div className="bg-surface border border-white/5 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-text/40 mb-1">
              Email addresses (comma or newline separated)
            </label>
            <textarea
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="user@example.com, another@example.com"
              rows={3}
              className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder:text-text/20 focus:outline-none focus:border-primary/50 resize-none font-body"
            />
          </div>
          <div className="max-w-sm">
            <label className="block text-xs text-text/40 mb-1">
              Note (optional)
            </label>
            <input
              type="text"
              value={inviteNote}
              onChange={(e) => setInviteNote(e.target.value)}
              maxLength={255}
              placeholder="e.g. Beta testers"
              className="w-full bg-bg border border-white/10 rounded-lg px-3 py-2 text-sm text-text placeholder:text-text/20 focus:outline-none focus:border-primary/50 font-body"
            />
          </div>
          <button
            onClick={handleInvite}
            disabled={inviting || !inviteEmail.trim()}
            className="px-4 py-2 text-sm bg-primary text-bg rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {inviting ? "Sending..." : "Send Invitations"}
          </button>

          {/* Results */}
          {inviteResult && (
            <div className="mt-4 space-y-2">
              <p className="text-sm text-text/60">
                {inviteResult.total_invited} invited,{" "}
                {inviteResult.total_emails_sent} emails sent
              </p>
              {inviteResult.results.map((r) => (
                <div
                  key={r.email}
                  className="flex items-center gap-3 text-sm py-1"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${r.email_sent ? "bg-green-400" : "bg-amber-400"}`}
                  />
                  <span className="text-text/80">{r.email}</span>
                  <code className="text-xs font-mono text-primary/60 bg-primary/5 px-2 py-0.5 rounded">
                    {r.invite_code}
                  </code>
                  {!r.email_sent && (
                    <span className="text-xs text-amber-400">
                      (email not sent — share code manually)
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Search */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search by email..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="flex-1 max-w-sm bg-surface border border-white/10 rounded-lg px-4 py-2 font-body text-sm text-text placeholder:text-text/30 focus:outline-none focus:border-primary/50"
        />
      </div>

      {/* Table */}
      <div className="bg-surface border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full font-body text-sm">
          <thead>
            <tr className="border-b border-white/5 text-text/40 text-xs uppercase tracking-wider">
              <th
                className="text-left px-4 py-3 cursor-pointer hover:text-text/60"
                onClick={() => toggleSort("email")}
              >
                Email {sortBy === "email" && (sortOrder === "asc" ? "↑" : "↓")}
              </th>
              <th className="text-left px-4 py-3">Status</th>
              <th className="text-left px-4 py-3">Admin</th>
              <th
                className="text-left px-4 py-3 cursor-pointer hover:text-text/60"
                onClick={() => toggleSort("created_at")}
              >
                Joined{" "}
                {sortBy === "created_at" && (sortOrder === "asc" ? "↑" : "↓")}
              </th>
              <th className="text-left px-4 py-3">Last Login</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && !data ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text/40">
                  <div
                    className="w-6 h-6 rounded-full border-2 border-primary/20 border-t-primary animate-spin mx-auto"
                    role="status"
                    aria-label="Loading"
                  />
                </td>
              </tr>
            ) : data?.users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text/40">
                  No users found
                </td>
              </tr>
            ) : (
              data?.users.map((user) => (
                <tr
                  key={user.id}
                  className="border-b border-white/5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                  onClick={() => router.push(`/admin/users/${user.id}`)}
                >
                  <td className="px-4 py-3 text-text">{user.email || "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-xs ${
                        user.is_active
                          ? "bg-green-500/10 text-green-400"
                          : "bg-red-500/10 text-red-400"
                      }`}
                    >
                      {user.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {user.is_admin && (
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-amber-500/10 text-amber-400">
                        Admin
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-text/60">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-text/60">
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleDateString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleStatus(user);
                      }}
                      className={`text-xs px-3 py-1 rounded border transition-colors ${
                        user.is_active
                          ? "border-red-500/20 text-red-400 hover:bg-red-500/10"
                          : "border-green-500/20 text-green-400 hover:bg-green-500/10"
                      }`}
                    >
                      {user.is_active ? "Disable" : "Enable"}
                    </button>
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
