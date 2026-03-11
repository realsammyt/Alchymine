"use client";

import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import { useIntake, useApi } from "@/lib/useApi";
import { getProfile, ProfileResponse } from "@/lib/api";

const SYSTEMS = [
  { key: "identity", label: "I", name: "Intelligence", color: "#DAA520" },
  { key: "healing", label: "H", name: "Healing", color: "#20B2AA" },
  { key: "wealth", label: "W", name: "Wealth", color: "#DAA520" },
  { key: "creative", label: "C", name: "Creative", color: "#9B4DCA" },
  { key: "perspective", label: "P", name: "Perspective", color: "#7B2D8E" },
] as const;

export default function ProfileSummaryCard() {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const { data: intake, loading: intakeLoading } = useIntake(userId);

  const profile = useApi<ProfileResponse>(
    userId ? () => getProfile(userId) : null,
    [userId],
  );

  if (intakeLoading || !intake?.fullName) return null;

  const identityData = profile.data?.identity;
  const lifePath = identityData?.life_path as number | undefined;
  const sunSign = identityData?.sun_sign as string | undefined;
  const archetype = identityData?.primary_archetype as string | undefined;

  return (
    <div className="card-surface border border-white/[0.06] rounded-2xl px-5 py-4 sm:px-6">
      <div className="flex flex-col items-center sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4 sm:items-start">
          <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 text-2xl">
            {archetype ? "🔮" : "✨"}
          </div>
          <div className="min-w-0">
            <h3 className="font-display text-lg font-light text-text truncate">
              {intake.fullName}
            </h3>
            <p className="font-body text-xs text-text/40 mt-0.5">
              {[
                lifePath != null ? `Life Path ${lifePath}` : null,
                sunSign ? `${sunSign} ☉` : null,
              ]
                .filter(Boolean)
                .join(" · ") || "Generating your profile…"}
            </p>
            {archetype && (
              <p className="font-body text-xs text-primary/70 mt-0.5">
                {archetype}
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-col items-center sm:items-end gap-2">
          <div className="flex items-center gap-2">
            {SYSTEMS.map(({ key, label, name, color }) => {
              const filled = profile.data
                ? profile.data[key as keyof ProfileResponse] !== null
                : false;
              return (
                <div
                  key={key}
                  data-testid={`system-dot-${key}`}
                  title={`${name}: ${filled ? "Active" : "Not started"}`}
                  className="flex flex-col items-center gap-1"
                >
                  <div
                    className="w-3 h-3 rounded-full transition-all duration-300"
                    style={{
                      background: filled ? color : "rgba(255,255,255,0.06)",
                      border: filled
                        ? `1.5px solid ${color}`
                        : "1.5px solid rgba(255,255,255,0.1)",
                      boxShadow: filled ? `0 0 8px ${color}44` : "none",
                    }}
                  />
                  <span className="text-[9px] font-body text-text/25">
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
          <Link
            href="/profile"
            className="font-body text-xs text-primary/60 hover:text-primary transition-colors no-underline"
          >
            View Full Profile →
          </Link>
        </div>
      </div>
    </div>
  );
}
