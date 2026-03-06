"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  adminGetUser,
  adminUpdateUserStatus,
  adminToggleAdmin,
} from "@/lib/api";
import type { AdminUserDetail } from "@/lib/api";

export default function AdminUserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = async () => {
    try {
      const data = await adminGetUser(userId);
      setUser(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load user");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, [userId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggleStatus = async () => {
    if (!user) return;
    await adminUpdateUserStatus(user.id, !user.is_active);
    fetchUser();
  };

  const handleToggleAdmin = async () => {
    if (!user) return;
    await adminToggleAdmin(user.id, !user.is_admin);
    fetchUser();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div
          className="w-8 h-8 rounded-full border-2 border-primary/20 border-t-primary animate-spin"
          role="status"
          aria-label="Loading"
        />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="text-center py-12">
        <p className="font-body text-red-400">{error || "User not found"}</p>
        <button
          onClick={() => router.back()}
          className="mt-4 font-body text-sm text-primary hover:underline"
        >
          Go back
        </button>
      </div>
    );
  }

  const profiles = [
    { name: "Intake", complete: user.has_intake },
    { name: "Identity", complete: user.has_identity },
    { name: "Healing", complete: user.has_healing },
    { name: "Wealth", complete: user.has_wealth },
    { name: "Creative", complete: user.has_creative },
    { name: "Perspective", complete: user.has_perspective },
  ];

  const completedCount = profiles.filter((p) => p.complete).length;

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.back()}
            className="font-body text-xs text-text/40 hover:text-text/60 mb-2 block"
          >
            &larr; Back to Users
          </button>
          <h1 className="font-display text-2xl text-text font-light">
            {user.email || "No email"}
          </h1>
          <p className="font-body text-xs text-text/40 mt-1">ID: {user.id}</p>
        </div>
        <div className="flex gap-2">
          <span
            className={`inline-block px-2 py-0.5 rounded-full text-xs ${
              user.is_active
                ? "bg-green-500/10 text-green-400"
                : "bg-red-500/10 text-red-400"
            }`}
          >
            {user.is_active ? "Active" : "Disabled"}
          </span>
          {user.is_admin && (
            <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-amber-500/10 text-amber-400">
              Admin
            </span>
          )}
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "Version", value: user.version },
          {
            label: "Joined",
            value: new Date(user.created_at).toLocaleString(),
          },
          {
            label: "Last Updated",
            value: new Date(user.updated_at).toLocaleString(),
          },
          {
            label: "Last Login",
            value: user.last_login_at
              ? new Date(user.last_login_at).toLocaleString()
              : "Never",
          },
          { label: "Invite Code Used", value: user.invite_code_used || "None" },
        ].map((item) => (
          <div
            key={item.label}
            className="bg-surface border border-white/5 rounded-lg p-4"
          >
            <p className="font-body text-xs text-text/40 uppercase tracking-wider">
              {item.label}
            </p>
            <p className="font-body text-sm text-text mt-1">{item.value}</p>
          </div>
        ))}
      </div>

      {/* Profile Completeness */}
      <div className="bg-surface border border-white/5 rounded-xl p-6">
        <h2 className="font-display text-lg text-text font-light mb-4">
          Profile Completeness ({completedCount}/{profiles.length})
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {profiles.map((p) => (
            <div
              key={p.name}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg font-body text-sm ${
                p.complete
                  ? "bg-green-500/10 text-green-400"
                  : "bg-white/5 text-text/30"
              }`}
            >
              <span>{p.complete ? "✓" : "○"}</span>
              {p.name}
            </div>
          ))}
        </div>
      </div>

      {/* Account Controls */}
      <div className="bg-surface border border-white/5 rounded-xl p-6 space-y-4">
        <h2 className="font-display text-lg text-text font-light">
          Account Controls
        </h2>
        <div className="flex gap-3">
          <button
            onClick={handleToggleStatus}
            className={`px-4 py-2 font-body text-sm rounded-lg border transition-colors ${
              user.is_active
                ? "border-red-500/20 text-red-400 hover:bg-red-500/10"
                : "border-green-500/20 text-green-400 hover:bg-green-500/10"
            }`}
          >
            {user.is_active ? "Disable Account" : "Enable Account"}
          </button>
          <button
            onClick={handleToggleAdmin}
            className={`px-4 py-2 font-body text-sm rounded-lg border transition-colors ${
              user.is_admin
                ? "border-amber-500/20 text-amber-400 hover:bg-amber-500/10"
                : "border-primary/20 text-primary hover:bg-primary/10"
            }`}
          >
            {user.is_admin ? "Revoke Admin" : "Grant Admin"}
          </button>
        </div>
      </div>
    </div>
  );
}
