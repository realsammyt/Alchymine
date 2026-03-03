"use client";

import {
  MotionStagger,
  MotionStaggerItem,
} from "@/components/shared/MotionReveal";

interface Step {
  label: string;
  path: string;
}

interface StepIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export default function StepIndicator({
  steps,
  currentStep,
}: StepIndicatorProps) {
  return (
    <MotionStagger
      staggerDelay={0.07}
      className="flex items-center justify-center gap-1 sm:gap-2"
    >
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        return (
          <MotionStaggerItem key={step.label} className="flex items-center">
            {/* Step circle + label */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-all duration-500 border ${
                  isCompleted
                    ? "bg-primary border-primary text-bg"
                    : isCurrent
                      ? "bg-primary/20 border-primary/40 text-primary glow-gold"
                      : "bg-white/[0.03] border-white/[0.08] text-text/30"
                }`}
                aria-current={isCurrent ? "step" : undefined}
              >
                {isCompleted ? (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  index + 1
                )}
              </div>
              <span
                className={`mt-1.5 font-body text-xs tracking-wide transition-all duration-500 ${
                  isCompleted
                    ? "text-primary"
                    : isCurrent
                      ? "text-primary font-medium"
                      : "text-text/30"
                }`}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < steps.length - 1 && (
              <div
                className={`w-8 sm:w-12 h-0.5 mx-1 sm:mx-2 mt-[-16px] transition-all duration-500 ${
                  isCompleted ? "bg-primary/30" : "bg-white/[0.06]"
                }`}
                aria-hidden="true"
              />
            )}
          </MotionStaggerItem>
        );
      })}
    </MotionStagger>
  );
}
