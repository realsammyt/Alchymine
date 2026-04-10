"use client";

import Link from "next/link";
import { getBridges, BridgeResponse } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import ApiStateView from "./ApiStateView";
import {
  MotionStagger,
  MotionStaggerItem,
} from "./MotionReveal";

// ── System display config ────────────────────────────────────────

interface SystemStyle {
  label: string;
  href: string;
  accentText: string;
  accentBorder: string;
  tagBg: string;
}

const SYSTEM_STYLES: Record<string, SystemStyle> = {
  intelligence: {
    label: "Personal Intelligence",
    href: "/intelligence",
    accentText: "text-primary",
    accentBorder: "border-primary/20",
    tagBg: "bg-primary/10 text-primary",
  },
  healing: {
    label: "Ethical Healing",
    href: "/healing",
    accentText: "text-accent",
    accentBorder: "border-accent/20",
    tagBg: "bg-accent/10 text-accent",
  },
  wealth: {
    label: "Generational Wealth",
    href: "/wealth",
    accentText: "text-primary",
    accentBorder: "border-primary/20",
    tagBg: "bg-primary/10 text-primary",
  },
  creative: {
    label: "Creative Forge",
    href: "/creative",
    accentText: "text-secondary-light",
    accentBorder: "border-secondary/20",
    tagBg: "bg-secondary/10 text-secondary-light",
  },
  perspective: {
    label: "Perspective Prism",
    href: "/perspective",
    accentText: "text-accent",
    accentBorder: "border-accent/20",
    tagBg: "bg-accent/10 text-accent",
  },
};

function getStyle(system: string): SystemStyle {
  return (
    SYSTEM_STYLES[system] ?? {
      label: system,
      href: `/${system}`,
      accentText: "text-primary",
      accentBorder: "border-primary/20",
      tagBg: "bg-primary/10 text-primary",
    }
  );
}

// ── Arrow icon ───────────────────────────────────────────────────

function ArrowRight({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "w-4 h-4"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}

// ── Bridge card ──────────────────────────────────────────────────

function BridgeCard({ bridge }: { bridge: BridgeResponse }) {
  const targetStyle = getStyle(bridge.target_system);

  return (
    <div
      className={`card-surface border ${targetStyle.accentBorder} p-5 h-full transition-all duration-300 hover:-translate-y-0.5`}
      data-testid={`bridge-card-${bridge.id}`}
    >
      {/* Header: source → target */}
      <div className="flex items-center gap-2 mb-3">
        <span className="font-body text-xs tracking-wider uppercase text-text/40">
          {getStyle(bridge.source_system).label}
        </span>
        <ArrowRight className="w-3 h-3 text-text/30 flex-shrink-0" />
        <span
          className={`font-body text-xs tracking-wider uppercase ${targetStyle.accentText}`}
        >
          {targetStyle.label}
        </span>
      </div>

      {/* Bridge name */}
      <h3
        className={`font-display text-sm font-medium ${targetStyle.accentText} mb-2`}
      >
        {bridge.name}
      </h3>

      {/* Description */}
      <p className="font-body text-sm text-text/50 leading-relaxed mb-4">
        {bridge.description}
      </p>

      {/* Insight key tags */}
      {bridge.insight_keys.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {bridge.insight_keys.map((key) => (
            <span
              key={key}
              className={`font-body text-[0.65rem] tracking-wider px-2 py-0.5 rounded-full ${targetStyle.tagBg}`}
            >
              {key.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Link to target system */}
      <Link
        href={targetStyle.href}
        className={`font-body text-xs ${targetStyle.accentText} underline underline-offset-2`}
      >
        Explore {targetStyle.label} &rarr;
      </Link>
    </div>
  );
}

// ── Main panel ───────────────────────────────────────────────────

interface CrossSystemBridgePanelProps {
  /** The current system key (healing, wealth, creative, intelligence, perspective). */
  system: string;
}

export default function CrossSystemBridgePanel({
  system,
}: CrossSystemBridgePanelProps) {
  const {
    data: bridges,
    loading,
    error,
    refetch,
  } = useApi<BridgeResponse[]>(
    () => getBridges(system),
    [system],
  );

  const hasBridges = bridges && bridges.length > 0;

  return (
    <section
      className="mb-12"
      aria-labelledby="cross-system-bridges-heading"
      data-testid="cross-system-bridges"
    >
      <ApiStateView
        loading={loading}
        error={error}
        empty={!hasBridges && !loading}
        emptyText="No cross-system bridges found for this system."
        emptyIcon={"\u{1F517}"}
        loadingText="Loading cross-system connections..."
        onRetry={refetch}
      >
        <h2
          id="cross-system-bridges-heading"
          className="font-display text-xl font-light text-text/80 mb-5"
        >
          Cross-System Connections
        </h2>
        <MotionStagger className="grid sm:grid-cols-2 gap-4">
          {bridges?.map((bridge) => (
            <MotionStaggerItem key={bridge.id}>
              <BridgeCard bridge={bridge} />
            </MotionStaggerItem>
          ))}
        </MotionStagger>
      </ApiStateView>
    </section>
  );
}
