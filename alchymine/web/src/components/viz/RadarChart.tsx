"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";

type RadarChartProps = {
  scores: Record<string, number>;
  maxScore?: number;
  size?: number;
};

/**
 * 6-point radar chart for Guilford creativity scores.
 * Renders an animated SVG polygon.
 */
export function RadarChart({
  scores,
  maxScore = 100,
  size = 220,
}: RadarChartProps) {
  const prefersReducedMotion = useReducedMotion();

  const keys = Object.keys(scores).slice(0, 6);
  const numAxes = keys.length;
  const center = size / 2;
  const maxRadius = size / 2 - 28;
  const labelOffset = 18;

  const axisAngle = (index: number) =>
    (2 * Math.PI * index) / numAxes - Math.PI / 2;

  const polarToCartesian = (r: number, angle: number) => ({
    x: center + r * Math.cos(angle),
    y: center + r * Math.sin(angle),
  });

  // Background grid rings
  const gridRings = [0.25, 0.5, 0.75, 1].map(
    (factor) =>
      keys
        .map((_, i) => {
          const pt = polarToCartesian(maxRadius * factor, axisAngle(i));
          return `${i === 0 ? "M" : "L"} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
        })
        .join(" ") + " Z",
  );

  // Data polygon
  const dataPoints = useMemo(
    () =>
      keys.map((key, i) => {
        const value = Math.min(maxScore, Math.max(0, scores[key] ?? 0));
        const r = (value / maxScore) * maxRadius;
        return polarToCartesian(r, axisAngle(i));
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [keys, scores, maxScore, maxRadius],
  );

  const emptyPolygon = keys
    .map((_, i) => {
      const pt = polarToCartesian(0, axisAngle(i));
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
    })
    .join(" ");

  const dataPolygon = dataPoints
    .map((pt) => `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`)
    .join(" ");

  // Labels
  const labels = keys.map((key, i) => {
    const angle = axisAngle(i);
    const pt = polarToCartesian(maxRadius + labelOffset, angle);
    return { key, x: pt.x, y: pt.y };
  });

  return (
    <div
      role="img"
      aria-label={`Radar chart: ${keys.map((k) => `${k} ${scores[k]}`).join(", ")}`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-hidden="true"
      >
        {/* Grid rings */}
        {gridRings.map((d, i) => (
          <path
            key={i}
            d={d}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={1}
          />
        ))}

        {/* Axis lines */}
        {keys.map((_, i) => {
          const end = polarToCartesian(maxRadius, axisAngle(i));
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={end.x.toFixed(1)}
              y2={end.y.toFixed(1)}
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={1}
            />
          );
        })}

        {/* Data polygon */}
        <motion.polygon
          points={dataPolygon}
          fill="rgba(218, 165, 32, 0.15)"
          stroke="rgba(218, 165, 32, 0.7)"
          strokeWidth={1.5}
          strokeLinejoin="round"
          initial={{
            points: prefersReducedMotion ? dataPolygon : emptyPolygon,
            opacity: 0,
          }}
          animate={{ points: dataPolygon, opacity: 1 }}
          transition={
            prefersReducedMotion
              ? { duration: 0.01 }
              : { duration: 0.8, ease: [0.22, 1, 0.36, 1] }
          }
        />

        {/* Data point dots */}
        {dataPoints.map((pt, i) => (
          <motion.circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r={3}
            fill="#daa520"
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{
              duration: prefersReducedMotion ? 0.01 : 0.3,
              delay: prefersReducedMotion ? 0 : 0.7 + i * 0.05,
            }}
            style={{ transformOrigin: `${pt.x}px ${pt.y}px` }}
          />
        ))}

        {/* Labels */}
        {labels.map(({ key, x, y }) => (
          <text
            key={key}
            x={x.toFixed(1)}
            y={y.toFixed(1)}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={10}
            fill="rgba(255,255,255,0.5)"
            fontFamily="var(--font-body, sans-serif)"
          >
            {key}
          </text>
        ))}
      </svg>
    </div>
  );
}
