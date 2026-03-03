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

  return (
    <div
      className={`card-surface p-6 transition-all duration-300 ${className}`}
    >
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
              className={`px-3 py-1 rounded-full text-xs font-medium ${badgeColor}`}
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
