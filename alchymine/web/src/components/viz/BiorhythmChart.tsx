"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useMemo } from "react";

type BiorhythmChartProps = {
  birthDate: string;
  currentDate?: string;
  width?: number;
  height?: number;
};

const CYCLES = [
  { key: "physical", period: 23, color: "#f0c050", label: "Physical" },
  { key: "emotional", period: 28, color: "#9b4dca", label: "Emotional" },
  { key: "intellectual", period: 33, color: "#20b2aa", label: "Intellectual" },
] as const;

const DAY_WINDOW = 30;

function daysSinceBirth(birthDate: string, targetDate: string): number {
  const birth = new Date(birthDate).getTime();
  const target = new Date(targetDate).getTime();
  return Math.floor((target - birth) / (1000 * 60 * 60 * 24));
}

/**
 * Simple SVG sine-wave biorhythm chart.
 * Shows physical / emotional / intellectual cycles over a 30-day window.
 */
export function BiorhythmChart({
  birthDate,
  currentDate,
  width = 320,
  height = 160,
}: BiorhythmChartProps) {
  const prefersReducedMotion = useReducedMotion();

  const today = currentDate ?? new Date().toISOString().slice(0, 10);
  const paddingX = 16;
  const paddingY = 16;
  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;
  const midY = paddingY + chartHeight / 2;

  const totalDaysAtToday = useMemo(
    () => daysSinceBirth(birthDate, today),
    [birthDate, today],
  );

  // Generate SVG path for each cycle over the 30-day window
  const paths = useMemo(() => {
    return CYCLES.map(({ period, color }) => {
      const startDay = totalDaysAtToday - Math.floor(DAY_WINDOW / 2);
      const points: string[] = [];

      for (let i = 0; i <= DAY_WINDOW; i++) {
        const dayOffset = startDay + i;
        const value = Math.sin((2 * Math.PI * dayOffset) / period);
        const x = paddingX + (i / DAY_WINDOW) * chartWidth;
        const y = midY - value * (chartHeight / 2 - 4);
        points.push(`${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`);
      }

      return { d: points.join(" "), color };
    });
  }, [totalDaysAtToday, chartWidth, chartHeight, midY]);

  // X position for "today" marker (center of window)
  const todayX = paddingX + (DAY_WINDOW / 2 / DAY_WINDOW) * chartWidth;

  return (
    <div className="flex flex-col gap-3">
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Biorhythm chart showing physical, emotional, and intellectual cycles"
        className="overflow-visible"
      >
        {/* Zero line */}
        <line
          x1={paddingX}
          y1={midY}
          x2={width - paddingX}
          y2={midY}
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={1}
        />

        {/* Cycle paths */}
        {paths.map(({ d, color }, idx) => (
          <motion.path
            key={idx}
            d={d}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.8}
            initial={prefersReducedMotion ? { opacity: 0.8 } : { opacity: 0 }}
            animate={{ opacity: 0.8 }}
            transition={{ duration: 0.6, delay: idx * 0.15 }}
          />
        ))}

        {/* Today marker */}
        <line
          x1={todayX}
          y1={paddingY}
          x2={todayX}
          y2={height - paddingY}
          stroke="rgba(218, 165, 32, 0.5)"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
        <circle
          cx={todayX}
          cy={paddingY}
          r={3}
          fill="rgba(218, 165, 32, 0.8)"
        />
      </svg>

      {/* Legend */}
      <div className="flex gap-4 justify-center flex-wrap">
        {CYCLES.map(({ key, color, label }) => (
          <div key={key} className="flex items-center gap-1.5">
            <div
              className="rounded-full"
              style={{ width: 8, height: 8, backgroundColor: color }}
            />
            <span className="text-xs text-text/50">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
