"use client";

import { motion, useReducedMotion } from "framer-motion";

type KeganStageLadderProps = {
  currentStage: 1 | 2 | 3 | 4 | 5;
  showLabels?: boolean;
};

const STAGES = [
  { stage: 1 as const, name: "Impulsive", description: "Driven by impulses" },
  {
    stage: 2 as const,
    name: "Imperial",
    description: "Self-interest centered",
  },
  {
    stage: 3 as const,
    name: "Socializing",
    description: "Defined by relationships",
  },
  {
    stage: 4 as const,
    name: "Self-Authoring",
    description: "Inner-directed identity",
  },
  {
    stage: 5 as const,
    name: "Self-Transforming",
    description: "Holds multiple frames",
  },
] as const;

/**
 * Vertical ladder visualization for Kegan's orders of consciousness.
 * The current stage is highlighted in gold; completed stages show dimly.
 */
export function KeganStageLadder({
  currentStage,
  showLabels = true,
}: KeganStageLadderProps) {
  const prefersReducedMotion = useReducedMotion();

  // Render highest stage first (top = most developed)
  const orderedStages = [...STAGES].reverse();

  return (
    <div
      className="flex flex-col gap-2 w-full"
      role="list"
      aria-label={`Kegan development stages. Current stage: ${currentStage}`}
    >
      {orderedStages.map(({ stage, name, description }, i) => {
        const isActive = stage === currentStage;
        const isCompleted = stage < currentStage;

        return (
          <motion.div
            key={stage}
            role="listitem"
            aria-current={isActive ? "true" : undefined}
            className="flex items-center gap-3"
            initial={
              prefersReducedMotion ? { opacity: 1 } : { opacity: 0, x: -12 }
            }
            animate={{ opacity: 1, x: 0 }}
            transition={{
              duration: prefersReducedMotion ? 0.01 : 0.4,
              delay: prefersReducedMotion ? 0 : i * 0.07,
              ease: [0.22, 1, 0.36, 1],
            }}
          >
            {/* Stage number badge */}
            <div
              className="flex-shrink-0 flex items-center justify-center rounded-full font-body font-semibold text-sm"
              style={{
                width: 32,
                height: 32,
                background: isActive
                  ? "linear-gradient(135deg, #b8860b, #f0c050)"
                  : isCompleted
                    ? "rgba(218, 165, 32, 0.15)"
                    : "rgba(255, 255, 255, 0.05)",
                color: isActive
                  ? "#0A0A0F"
                  : isCompleted
                    ? "rgba(218, 165, 32, 0.6)"
                    : "rgba(255,255,255,0.2)",
                boxShadow: isActive
                  ? "0 0 16px rgba(218, 165, 32, 0.3)"
                  : "none",
              }}
            >
              {stage}
            </div>

            {/* Bar + label */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-sm font-body font-medium truncate"
                  style={{
                    color: isActive
                      ? "#f0c050"
                      : isCompleted
                        ? "rgba(218, 165, 32, 0.5)"
                        : "rgba(255,255,255,0.2)",
                  }}
                >
                  {name}
                </span>
                {isActive && (
                  <span className="text-xs text-text/30 font-body truncate">
                    — current
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div
                className="h-1.5 rounded-full overflow-hidden"
                style={{ background: "rgba(255,255,255,0.05)" }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background: isActive
                      ? "linear-gradient(90deg, #b8860b, #f0c050)"
                      : isCompleted
                        ? "rgba(218, 165, 32, 0.3)"
                        : "transparent",
                  }}
                  initial={{ width: 0 }}
                  animate={{
                    width: isActive ? "75%" : isCompleted ? "100%" : "0%",
                  }}
                  transition={
                    prefersReducedMotion
                      ? { duration: 0.01 }
                      : {
                          duration: 0.6,
                          delay: i * 0.07 + 0.2,
                          ease: [0.22, 1, 0.36, 1],
                        }
                  }
                />
              </div>

              {showLabels && (
                <p
                  className="text-xs mt-0.5 truncate"
                  style={{
                    color: isActive
                      ? "rgba(255,255,255,0.4)"
                      : "rgba(255,255,255,0.12)",
                  }}
                >
                  {description}
                </p>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
