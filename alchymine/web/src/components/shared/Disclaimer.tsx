import { COPY } from "@/lib/copy";

type DisclaimerType = keyof typeof COPY.disclaimers;

interface DisclaimerProps {
  type: DisclaimerType;
}

export default function Disclaimer({ type }: DisclaimerProps) {
  return (
    <p className="flex items-start gap-1.5 text-xs text-text/40 leading-relaxed mt-2">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="shrink-0 mt-0.5"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </svg>
      {COPY.disclaimers[type]}
    </p>
  );
}
