"use client";

interface QualityCheck {
  name: string;
  passed: boolean;
}

interface QualityGateDisplayProps {
  checksPassed: number;
  checksTotal: number;
  checks?: QualityCheck[];
}

const DEFAULT_CHECKS: QualityCheck[] = [
  { name: "Ethics", passed: true },
  { name: "Accuracy", passed: true },
  { name: "Completeness", passed: true },
  { name: "Safety", passed: true },
  { name: "Bias", passed: true },
];

export default function QualityGateDisplay({
  checksPassed,
  checksTotal,
  checks = DEFAULT_CHECKS,
}: QualityGateDisplayProps) {
  const allPassed = checksPassed === checksTotal;

  return (
    <div
      data-testid="quality-gate-display"
      className="inline-flex flex-col gap-2"
    >
      {/* Summary row */}
      <div className="inline-flex items-center gap-2">
        {/* Shield icon */}
        <svg
          className={`w-3.5 h-3.5 flex-shrink-0 ${allPassed ? "text-accent/60" : "text-primary/60"}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
          {allPassed && <path d="m9 12 2 2 4-4" />}
        </svg>
        <span
          className="text-[11px] font-body text-text/40"
          aria-label={`Verified: ${checksPassed} of ${checksTotal} quality checks passed`}
        >
          Verified:{" "}
          <span
            className={
              allPassed ? "text-accent/70 font-medium" : "text-primary/70 font-medium"
            }
          >
            {checksPassed}/{checksTotal}
          </span>{" "}
          quality checks passed
        </span>
      </div>

      {/* Individual checks */}
      {checks.length > 0 && (
        <div
          className="flex flex-wrap gap-x-3 gap-y-1"
          role="list"
          aria-label="Quality check results"
        >
          {checks.map((check) => (
            <div
              key={check.name}
              role="listitem"
              className="inline-flex items-center gap-1"
              aria-label={`${check.name}: ${check.passed ? "passed" : "failed"}`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                  check.passed ? "bg-accent/50" : "bg-primary-dark/50"
                }`}
                aria-hidden="true"
              />
              <span
                className={`text-[10px] font-body ${
                  check.passed ? "text-text/35" : "text-primary-dark/60"
                }`}
              >
                {check.name}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
