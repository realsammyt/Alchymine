'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';

// ── Types ─────────────────────────────────────────────────────────

interface SystemRecommendation {
  system: string;
  score: number;
  reason: string;
  entry_action: string;
  priority: number;
}

interface SpiralRouteResult {
  primary_system: string;
  recommendations: SystemRecommendation[];
  for_you_today: string;
  evidence_level: string;
  calculation_type: string;
  methodology: string;
}

// ── Constants ─────────────────────────────────────────────────────

const GUIDED_INTENTIONS = [
  {
    key: 'self-understanding',
    label: 'I want to understand myself better',
    icon: '\u{1F52E}',
    category: 'intelligence',
  },
  {
    key: 'financial-decision',
    label: 'I need to make a financial decision',
    icon: '\u{1F4B0}',
    category: 'wealth',
  },
  {
    key: 'creative-block',
    label: "I'm feeling stuck creatively",
    icon: '\u{1F3A8}',
    category: 'creative',
  },
  {
    key: 'emotional-healing',
    label: 'I want to heal emotionally',
    icon: '\u{1F331}',
    category: 'healing',
  },
  {
    key: 'career-direction',
    label: 'I need career direction',
    icon: '\u{1F4BC}',
    category: 'intelligence',
  },
  {
    key: 'build-wealth',
    label: 'I want to build generational wealth',
    icon: '\u{1F48E}',
    category: 'wealth',
  },
  {
    key: 'perspective-shift',
    label: 'I want to see things differently',
    icon: '\u{1F52D}',
    category: 'perspective',
  },
  {
    key: 'relationship-growth',
    label: 'I want to improve my relationships',
    icon: '\u{2764}\u{FE0F}',
    category: 'healing',
  },
  {
    key: 'find-purpose',
    label: 'I want to find my purpose',
    icon: '\u{1F9ED}',
    category: 'intelligence',
  },
  {
    key: 'legacy-planning',
    label: 'I want to build a lasting legacy',
    icon: '\u{1F3DB}\u{FE0F}',
    category: 'wealth',
  },
];

const SYSTEM_META: Record<
  string,
  { label: string; color: string; icon: string; path: string; tagline: string }
> = {
  intelligence: {
    label: 'Personalized Intelligence',
    color: '#6366f1',
    icon: '\u{1F52E}',
    path: '/intelligence',
    tagline: 'Know yourself deeply',
  },
  healing: {
    label: 'Ethical Healing',
    color: '#10b981',
    icon: '\u{1F331}',
    path: '/healing',
    tagline: 'Heal with integrity',
  },
  wealth: {
    label: 'Generational Wealth',
    color: '#f59e0b',
    icon: '\u{1F48E}',
    path: '/wealth',
    tagline: 'Build lasting prosperity',
  },
  creative: {
    label: 'Creative Development',
    color: '#ec4899',
    icon: '\u{1F3A8}',
    path: '/creative',
    tagline: 'Express your vision',
  },
  perspective: {
    label: 'Perspective Enhancement',
    color: '#8b5cf6',
    icon: '\u{1F52D}',
    path: '/perspective',
    tagline: 'Expand your worldview',
  },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Spiral Visual ─────────────────────────────────────────────────

function SpiralVisual({ active, primarySystem }: { active: boolean; primarySystem: string | null }) {
  const color = primarySystem ? SYSTEM_META[primarySystem]?.color || '#6366f1' : '#6366f1';

  return (
    <div
      className="spiral-visual-container"
      style={{
        position: 'relative',
        width: 200,
        height: 200,
        margin: '0 auto 2rem',
      }}
    >
      {/* Outer glow ring */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: `radial-gradient(circle at center, ${color}15 0%, transparent 70%)`,
          animation: active ? 'spiralPulse 3s ease-in-out infinite' : undefined,
        }}
      />
      {/* Middle ring */}
      <div
        style={{
          position: 'absolute',
          inset: 20,
          borderRadius: '50%',
          border: `2px solid ${color}33`,
          animation: active ? 'spiralRotate 8s linear infinite' : undefined,
          background: `conic-gradient(from 0deg, ${color}11, ${color}22, ${color}11, transparent)`,
        }}
      />
      {/* Inner ring */}
      <div
        style={{
          position: 'absolute',
          inset: 45,
          borderRadius: '50%',
          border: `2px solid ${color}55`,
          animation: active ? 'spiralRotate 5s linear infinite reverse' : undefined,
          background: `conic-gradient(from 180deg, ${color}22, ${color}33, ${color}22, transparent)`,
        }}
      />
      {/* Core circle */}
      <div
        style={{
          position: 'absolute',
          inset: 70,
          borderRadius: '50%',
          background: `radial-gradient(circle at center, ${color}44, ${color}22)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          animation: active ? 'spiralPulse 2s ease-in-out infinite' : undefined,
        }}
      >
        <span style={{ fontSize: '1.5rem' }}>
          {primarySystem ? SYSTEM_META[primarySystem]?.icon || '\u{2728}' : '\u{2728}'}
        </span>
      </div>
      {/* Five system dots around the spiral */}
      {Object.entries(SYSTEM_META).map(([key, meta], i) => {
        const angle = (i * 72 - 90) * (Math.PI / 180);
        const radius = 88;
        const x = 100 + radius * Math.cos(angle) - 8;
        const y = 100 + radius * Math.sin(angle) - 8;
        const isActive = primarySystem === key;
        return (
          <div
            key={key}
            title={meta.label}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: 16,
              height: 16,
              borderRadius: '50%',
              background: isActive ? meta.color : `${meta.color}44`,
              border: isActive ? `2px solid ${meta.color}` : '1px solid transparent',
              transition: 'all 0.4s ease',
              transform: isActive ? 'scale(1.4)' : 'scale(1)',
              boxShadow: isActive ? `0 0 12px ${meta.color}66` : 'none',
            }}
          />
        );
      })}
      <style jsx>{`
        @keyframes spiralPulse {
          0%, 100% { opacity: 0.7; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.05); }
        }
        @keyframes spiralRotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// ── Recommendation Card ──────────────────────────────────────────

function RecommendationCard({
  rec,
  isPrimary,
}: {
  rec: SystemRecommendation;
  isPrimary: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const meta = SYSTEM_META[rec.system];
  if (!meta) return null;

  return (
    <Link href={meta.path} style={{ textDecoration: 'none', color: 'inherit' }}>
      <div
        role="article"
        aria-label={`${meta.label} recommendation`}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          background: isPrimary
            ? `linear-gradient(135deg, ${meta.color}18, #1e1e2e)`
            : hovered
              ? `linear-gradient(135deg, ${meta.color}0d, #1e1e2e)`
              : '#1e1e2e',
          borderRadius: 14,
          padding: '1.25rem 1.5rem',
          borderLeft: `4px solid ${meta.color}`,
          border: isPrimary ? `2px solid ${meta.color}55` : `1px solid ${hovered ? meta.color + '44' : '#333'}`,
          borderLeftWidth: 4,
          borderLeftStyle: 'solid',
          borderLeftColor: meta.color,
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
          boxShadow: hovered ? `0 4px 20px ${meta.color}22` : 'none',
        }}
      >
        {/* Header row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: `${meta.color}15`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
              }}
            >
              {meta.icon}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.95rem', color: '#e5e7eb' }}>
                  {meta.label}
                </span>
                {isPrimary && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      background: `${meta.color}22`,
                      color: meta.color,
                      padding: '2px 8px',
                      borderRadius: 20,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                    }}
                  >
                    Best Match
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 2 }}>
                {meta.tagline}
              </div>
            </div>
          </div>
        </div>

        {/* Confidence bar */}
        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: '0.7rem', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Confidence
            </span>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: meta.color }}>
              {rec.score.toFixed(0)}%
            </span>
          </div>
          <div style={{ width: '100%', height: 6, background: '#374151', borderRadius: 3, overflow: 'hidden' }}>
            <div
              style={{
                width: `${rec.score}%`,
                height: '100%',
                background: `linear-gradient(90deg, ${meta.color}88, ${meta.color})`,
                borderRadius: 3,
                transition: 'width 0.8s ease-out',
              }}
            />
          </div>
        </div>

        {/* Reason */}
        <p style={{ color: '#9ca3af', fontSize: '0.85rem', lineHeight: 1.5, marginBottom: '0.5rem' }}>
          {rec.reason}
        </p>

        {/* Action link */}
        <div
          style={{
            fontSize: '0.8rem',
            color: meta.color,
            fontWeight: 500,
            opacity: hovered ? 1 : 0.8,
            transition: 'opacity 0.2s',
          }}
        >
          {rec.entry_action} &rarr;
        </div>
      </div>
    </Link>
  );
}

// ── Component ─────────────────────────────────────────────────────

export default function SpiralHub() {
  const [selectedIntention, setSelectedIntention] = useState<string | null>(null);
  const [routeResult, setRouteResult] = useState<SpiralRouteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getRoute = useCallback(async (intentionKey: string) => {
    setSelectedIntention(intentionKey);
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/v1/spiral/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention: intentionKey }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SpiralRouteResult = await res.json();
      setRouteResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get routing');
    } finally {
      setLoading(false);
    }
  }, []);

  const primarySystem = routeResult?.primary_system || null;

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '2rem 1rem' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
        <p
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.15em',
            color: '#c4a04a',
            marginBottom: '0.75rem',
          }}
        >
          Your Transformation Hub
        </p>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, marginBottom: '0.5rem', color: '#e5e7eb' }}>
          The Alchemical Spiral
        </h1>
        <p style={{ color: '#6b7280', maxWidth: 560, margin: '0 auto', fontSize: '0.95rem', lineHeight: 1.6 }}>
          Choose what matters most to you right now, and we will guide you to the
          highest-leverage system for your growth.
        </p>
      </div>

      {/* Spiral Visual */}
      <SpiralVisual active={loading || !!routeResult} primarySystem={primarySystem} />

      {/* Intention Selection */}
      <div style={{ marginBottom: '2rem' }}>
        <h2
          style={{
            fontSize: '0.85rem',
            color: '#6b7280',
            textAlign: 'center',
            marginBottom: '1rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}
        >
          What brings you here today?
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '0.75rem',
          }}
        >
          {GUIDED_INTENTIONS.map(({ key, label, icon }) => {
            const isSelected = selectedIntention === key;
            return (
              <button
                key={key}
                onClick={() => getRoute(key)}
                aria-pressed={isSelected}
                data-testid={`intention-${key}`}
                style={{
                  background: isSelected ? '#6366f122' : '#1e1e2e',
                  border: isSelected ? '2px solid #6366f1' : '1px solid #333',
                  borderRadius: 12,
                  padding: '0.875rem 1rem',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.25s ease',
                  color: '#e5e7eb',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <span style={{ fontSize: '1.25rem', flexShrink: 0 }}>{icon}</span>
                <span style={{ fontSize: '0.85rem', fontWeight: 500, lineHeight: 1.3 }}>
                  {label}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
          <div
            style={{
              width: 40,
              height: 40,
              border: '3px solid #333',
              borderTopColor: '#6366f1',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              animation: 'spiralRotate 0.8s linear infinite',
            }}
          />
          <p style={{ color: '#9ca3af', fontSize: '0.9rem' }}>Calculating your optimal path...</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div
          role="alert"
          style={{
            color: '#ef4444',
            background: '#1e1e2e',
            padding: '0.75rem 1rem',
            borderRadius: 8,
            marginBottom: '1rem',
            border: '1px solid #ef444433',
            fontSize: '0.9rem',
          }}
        >
          {error}
        </div>
      )}

      {/* Route Results */}
      {routeResult && !loading && (
        <div data-testid="spiral-results">
          {/* For You Today */}
          <div
            style={{
              background: `linear-gradient(135deg, ${SYSTEM_META[routeResult.primary_system]?.color || '#6366f1'}18, #1e1e2e)`,
              borderRadius: 16,
              padding: '1.5rem',
              marginBottom: '2rem',
              border: `1px solid ${SYSTEM_META[routeResult.primary_system]?.color || '#6366f1'}33`,
            }}
          >
            <h3 style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              For You Today
            </h3>
            <p style={{ fontSize: '1.1rem', lineHeight: 1.7, color: '#e5e7eb' }}>
              {routeResult.for_you_today}
            </p>
          </div>

          {/* System Rankings */}
          <h3
            style={{
              fontSize: '0.85rem',
              color: '#6b7280',
              marginBottom: '1rem',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            Your Systems, Ranked
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {routeResult.recommendations.map((rec) => (
              <RecommendationCard
                key={rec.system}
                rec={rec}
                isPrimary={rec.priority === 1}
              />
            ))}
          </div>

          {/* Methodology */}
          <div
            style={{
              marginTop: '2rem',
              padding: '1rem 1.25rem',
              background: '#111827',
              borderRadius: 10,
              fontSize: '0.75rem',
              color: '#6b7280',
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: '#9ca3af' }}>Methodology:</strong> {routeResult.methodology}
            <br />
            <span>
              Evidence: {routeResult.evidence_level} | Calculation: {routeResult.calculation_type}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
