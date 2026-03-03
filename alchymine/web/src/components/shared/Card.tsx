"use client";

import { ReactNode, useState } from "react";

interface CardProps {
  title?: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  expandable?: boolean;
  defaultExpanded?: boolean;
  expandedContent?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function Card({
  title,
  subtitle,
  badge,
  badgeColor = "bg-primary/20 text-primary",
  expandable = false,
  defaultExpanded = false,
  expandedContent,
  children,
  className = "",
}: CardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Derive the accent gradient color from badgeColor for the top border line.
  // badgeColor examples: "bg-primary/20 text-primary", "bg-accent/20 text-accent"
  const accentBorderStyle = (() => {
    if (badgeColor.includes("text-primary")) {
      return "linear-gradient(90deg, transparent, rgba(218,165,32,0.5), transparent)";
    }
    if (badgeColor.includes("text-secondary")) {
      return "linear-gradient(90deg, transparent, rgba(123,45,142,0.5), transparent)";
    }
    if (badgeColor.includes("text-accent")) {
      return "linear-gradient(90deg, transparent, rgba(32,178,170,0.5), transparent)";
    }
    return "linear-gradient(90deg, transparent, rgba(218,165,32,0.3), transparent)";
  })();

  return (
    <div
      className={`card-surface backdrop-blur-sm p-6 transition-all duration-300 relative overflow-hidden ${className}`}
    >
      {/* Subtle top accent gradient line */}
      <span
        aria-hidden="true"
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: accentBorderStyle }}
      />
      {/* Header */}
      {(title || badge) && (
        <div className="flex items-start justify-between mb-4">
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-text">{title}</h3>
            )}
            {subtitle && (
              <p className="text-sm text-text/50 mt-1">{subtitle}</p>
            )}
          </div>
          {badge && (
            <span
              className={`px-3 py-1 rounded-full font-body text-[0.7rem] font-medium tracking-wider uppercase ${badgeColor}`}
            >
              {badge}
            </span>
          )}
        </div>
      )}

      {/* Content */}
      <div>{children}</div>

      {/* Expandable section */}
      {expandable && expandedContent && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-4 flex items-center gap-1 text-sm text-primary/70 hover:text-primary transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={`transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
            >
              <path d="m6 9 6 6 6-6" />
            </svg>
            {expanded ? "Hide methodology" : "Show methodology"}
          </button>
          {expanded && (
            <div className="mt-4 pt-4 border-t border-white/5 animate-fade-in">
              {expandedContent}
            </div>
          )}
        </>
      )}
    </div>
  );
}
