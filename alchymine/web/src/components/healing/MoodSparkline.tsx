"use client";

import { useMemo } from "react";

// ── Types ────────────────────────────────────────────────────────────

interface MoodDataPoint {
  /** ISO date string or label. */
  date: string;
  /** Mood score (1-10). */
  score: number;
}

interface MoodSparklineProps {
  /** Mood data points to render (newest last). Max 14 shown. */
  data: MoodDataPoint[];
  /** SVG width in pixels. Default 180. */
  width?: number;
  /** SVG height in pixels. Default 40. */
  height?: number;
  /** Stroke color. Default "#20b2aa" (teal accent). */
  color?: string;
  /** Optional label shown to the left of the sparkline. */
  label?: string;
}

// ── Component ────────────────────────────────────────────────────────

export default function MoodSparkline({
  data,
  width = 180,
  height = 40,
  color = "#20b2aa",
  label,
}: MoodSparklineProps) {
  // Use up to the last 14 entries that have scores
  const points = useMemo(() => {
    return data.filter((d) => d.score >= 1 && d.score <= 10).slice(-14);
  }, [data]);

  const { polyline, dots, average, gradientId } = useMemo(() => {
    if (points.length === 0) {
      return { polyline: "", dots: [], average: null, gradientId: "" };
    }

    const id = `mood-gradient-${Math.random().toString(36).slice(2, 8)}`;
    const padX = 4;
    const padY = 4;
    const innerW = width - padX * 2;
    const innerH = height - padY * 2;

    const minScore = 1;
    const maxScore = 10;

    const coords = points.map((p, i) => {
      const x =
        points.length === 1
          ? width / 2
          : padX + (i / (points.length - 1)) * innerW;
      const y =
        padY +
        innerH -
        ((p.score - minScore) / (maxScore - minScore)) * innerH;
      return { x, y, score: p.score, date: p.date };
    });

    const line = coords.map((c) => `${c.x},${c.y}`).join(" ");
    const avg = points.reduce((s, p) => s + p.score, 0) / points.length;

    return { polyline: line, dots: coords, average: avg, gradientId: id };
  }, [points, width, height]);

  if (points.length === 0) {
    return (
      <div
        className="flex items-center gap-2"
        data-testid="mood-sparkline-empty"
        role="img"
        aria-label={label ? `${label}: no mood data available` : "No mood data available"}
      >
        {label && (
          <span className="font-body text-xs text-text/40">{label}</span>
        )}
        <span className="font-body text-xs text-text/30 italic" aria-hidden="true">
          No mood data
        </span>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-2"
      data-testid="mood-sparkline"
    >
      {label && (
        <span className="font-body text-xs text-text/40 whitespace-nowrap">
          {label}
        </span>
      )}
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`Mood trend over ${points.length} entries, average ${average?.toFixed(1)}`}
        className="flex-shrink-0"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Filled area under the line */}
        {dots.length > 1 && (
          <polygon
            points={`${dots[0].x},${height} ${polyline} ${dots[dots.length - 1].x},${height}`}
            fill={`url(#${gradientId})`}
          />
        )}

        {/* Polyline */}
        <polyline
          points={polyline}
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Dots */}
        {dots.map((d, i) => (
          <circle
            key={i}
            cx={d.x}
            cy={d.y}
            r={points.length <= 7 ? 2.5 : 1.5}
            fill={color}
          >
            <title>
              {d.date}: {d.score}/10
            </title>
          </circle>
        ))}
      </svg>

      {average !== null && (
        <span
          className="font-body text-xs text-text/50 whitespace-nowrap"
          aria-label={`Average mood score: ${average.toFixed(1)} out of 10`}
        >
          avg {average.toFixed(1)}
        </span>
      )}
      {/* Screen-reader-only data summary */}
      <span className="sr-only">
        Mood entries: {points.map((p) => `${p.date}: ${p.score} out of 10`).join(", ")}.
      </span>
    </div>
  );
}
