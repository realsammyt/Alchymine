"use client";

import { useEffect, useState } from "react";
import { adminGetAnalyticsOverview, adminGetUserAnalytics } from "@/lib/api";
import type { AnalyticsOverview, UserAnalytics } from "@/lib/api";

export default function AdminDashboardPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [userAnalytics, setUserAnalytics] = useState<UserAnalytics | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([adminGetAnalyticsOverview(), adminGetUserAnalytics(30)])
      .then(([ov, ua]) => {
        setOverview(ov);
        setUserAnalytics(ua);
      })
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Failed to load analytics",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

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

  if (error || !overview) {
    return (
      <div className="text-center py-12">
        <p className="font-body text-red-400">
          {error ?? "Failed to load analytics"}
        </p>
      </div>
    );
  }

  const metrics: { label: string; value: number; color: string }[] = [
    {
      label: "Total Users",
      value: overview.total_users,
      color: "text-primary",
    },
    {
      label: "Active Users",
      value: overview.active_users,
      color: "text-green-400",
    },
    {
      label: "Admin Users",
      value: overview.admin_users,
      color: "text-amber-400",
    },
    {
      label: "New Today",
      value: overview.new_users_today,
      color: "text-blue-400",
    },
    {
      label: "New This Week",
      value: overview.new_users_week,
      color: "text-blue-300",
    },
    {
      label: "New This Month",
      value: overview.new_users_month,
      color: "text-blue-200",
    },
    {
      label: "Invite Codes",
      value: overview.total_invite_codes,
      color: "text-purple-400",
    },
    {
      label: "Active Codes",
      value: overview.active_invite_codes,
      color: "text-purple-300",
    },
    { label: "Reports", value: overview.total_reports, color: "text-teal-400" },
    {
      label: "Journal Entries",
      value: overview.total_journal_entries,
      color: "text-rose-400",
    },
  ];

  const maxCount =
    userAnalytics && userAnalytics.daily_counts.length > 0
      ? Math.max(...userAnalytics.daily_counts.map((d) => d.count), 1)
      : 1;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl text-text font-light">
          Admin Dashboard
        </h1>
        <p className="font-body text-sm text-text/50 mt-1">
          Platform overview and analytics
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {metrics.map((m) => (
          <div
            key={m.label}
            className="bg-surface border border-white/5 rounded-xl p-4 space-y-1"
          >
            <p className="font-body text-xs text-text/40 uppercase tracking-wider">
              {m.label}
            </p>
            <p className={`font-display text-2xl font-light ${m.color}`}>
              {m.value.toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {/* User Growth Chart */}
      {userAnalytics && userAnalytics.daily_counts.length > 0 && (
        <div className="bg-surface border border-white/5 rounded-xl p-6">
          <h2 className="font-display text-lg text-text font-light mb-4">
            New Users &mdash; Last 30 Days
          </h2>
          <div
            className="flex items-end gap-1 h-48"
            aria-label="Bar chart: new users per day"
          >
            {userAnalytics.daily_counts.map((day) => {
              const heightPct = maxCount > 0 ? (day.count / maxCount) * 100 : 0;
              return (
                <div
                  key={day.date}
                  className="flex-1 group relative"
                  title={`${day.date}: ${day.count} new users`}
                >
                  <div
                    className="w-full bg-primary/60 hover:bg-primary transition-colors rounded-t"
                    style={{ height: `${Math.max(heightPct, 2)}%` }}
                  />
                  {/* Hover tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-bg border border-white/10 rounded px-2 py-1 text-xs font-body text-text whitespace-nowrap z-10 pointer-events-none">
                    {day.date}: {day.count}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2">
            <span className="font-body text-[10px] text-text/30">
              {userAnalytics.daily_counts[0]?.date}
            </span>
            <span className="font-body text-[10px] text-text/30">
              {
                userAnalytics.daily_counts[
                  userAnalytics.daily_counts.length - 1
                ]?.date
              }
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
